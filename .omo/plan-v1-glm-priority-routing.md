# Plan v1 — GLM-5.2 Priority Routing, Parallel Reader/Brain, Pipeline Format Unification

**Author**: Prometheus (high variant)
**Date**: 2026-07-20
**Hands to**: Orchestrator (you — GLM-5.2 on deepinfra/zai-org/GLM-5.2)

---

## Part A — Provider Routing & Service Tiers

### A.1 DeepInfra pricing (verified live, 2026-07-20)

Tier multipliers: **Standard 1.0x**, **Priority 1.5x**, **Flex 0.8x**.

| Role | Model | $/Mtok in/out | Context | Tier |
|---|---|---|---|---|
| **Tier 0 Orchestrator (you)** | `deepinfra/zai-org/GLM-5.2` | TBD* | — | **Priority** (1.5x) |
| Tier 1 Speed Reader | `deepinfra/deepseek-v4-flash` | $0.09 / $0.018 cached, $0.18 out | 1024K | Flex (0.8x) |
| Tier 2 Planner/Critic | `deepinfra/qwen-3-235b-a22b-instruct-2507` | $0.09 / $0.55 | 256K | Standard |
| Tier 3 Heavy Reasoning | `deepinfra/deepseek-r1-0528` | $0.50 / $2.15 | 160K | Standard |
| Tier 4 Long Context | `deepinfra/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8` | $0.20 / $0.80 | 1024K | Flex |

\* GLM-5.2 not on public pricing page — check DeepInfra dashboard for your account's rate. Treat as ~Tier 0 cost equivalent to Sonnet 4.6 ($3/$15) until verified.

### A.2 Cost-Benefit Routing Decision Matrix

| Task shape | Route | Rationale |
|---|---|---|
| Formula gating, single-file edit | Tier 0 direct | Me — cost is paid by user's GLM-5.2 budget |
| Read N unfamiliar files | Tier 1 (flash) | 4.5x cheaper than Tier 0; cached reads ~80x cheaper |
| Plan synthesis, plan review | Tier 2 (qwen MoE) | 30x cheaper than Tier 0, planner-optimized MoE |
| 2+ failed fix attempts, hard debug | Tier 3 (r1) | Reasoning matters; standard tier fine (not latency-critical) |
| 200K+ token file dump | Tier 4 (llama maverick) | 1M context, flex tier = $0.16/$0.64 |
| Concurrent multi-window (this env) | Local parallel runner (Part C) | Zero model cost, session-isolated |

### A.3 Token usage patterns (from session history)

Inspected 20 sessions 2026-07-10 to 2026-07-20:
- 12 sessions < 35 messages → light lookups, single-file edits (Tier 1)
- 5 sessions 50-120 messages → formulation + gating (Tier 0 + Tier 1 deepinfra)
- 3 sessions 150-181 messages → heavy multi-day work (Tier 0 + Tier 2 + Tier 3)
- **Heaviest usage**: formula markdown reads, pipeline JSON output parsing, reference contract source reads
- **Costliest waste**: aborted librarian reads (this session, $0 wasted but latency lost), DeepLuna MCP spins never used

### A.4 Service tier escalation rule

| Condition | Default | Escalate to |
|---|---|---|
| User typing in chat (any latency frustration) | Standard | **Priority** (1.5x) — they explicitly said too slow |
| Background batch (parallel readers) | Flex (0.8x) | Standard only if flex timing > 5min |
| Hard debug with 2+ failed attempts | Standard | Priority only if user is waiting on answer |
| Plan/critique (async) | Flex | Standard if build blocked on plan |

---

## Part B — OpenCode Config Changes (3 edits remaining)

### B.1 Set GLM-5.2 orchestrator model to priority tier

In `opencode.json` under each model slot, OpenCode may not support `service_tier` field natively. Implement via env var in `env-guard.js`:

```js
output.env.DEEPINFRA_SERVICE_TIER = "priority"
```

DeepInfra SDK accepts `service_tier: "priority"` body param. If OpenCode provider doesn't forward it, add a small plugin that wraps the request. For now, set the env flag — it can be picked up by any DeepInfra-aware provider adapter.

### B.2 Disable DeepLuna MCP for OpenCode ONLY

Flip `enabled: true → false` in `opencode.json` for `deepluna_read` and `deepluna_fast_read` blocks. **Do not touch** `~/.codex/config.toml` — Codex keeps DeepLuna active. Already added `_note_overrides` marker.

### B.3 Wire 3 new API keys via shell env (not config file)

Never commit keys. User launches opencode from a shell that exports:
```powershell
$env:DEEPINFRA_API_KEY = "<key>"
$env:DEEPSEEK_API_KEY = "<key>"
$env:OPENCODE_GO_API_KEY = "<key>"
$env:OPENCODE_SESSION_ID = "win_$PID"  # any unique string per window
```

`env-guard.js` already updated to forward these into spawned shells. Add README note in `.opencode/parallel/README.md` (Part C).

### B.4 Provider verification step

First concrete action for orchestrator:
```powershell
# Each curl should return 200 + small JSON
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPINFRA_API_KEY" https://api.deepinfra.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:OPENCODE_GO_API_KEY" https://api.opencode.com/v1/models
```
If DeepInfra returns 200 → Tier 0/1/2/3 are live.
If DeepSeek returns 200 → DeepSeek-direct MCP still usable as fallback.
If OpenCode Go returns 200 → new provider, sample it before production.

---

## Part C — Parallel Reader/Brain Framework (concurrent OpenCode isolation)

### C.1 Directory layout

```
.opencode/parallel/
├── README.md              # 50 lines — contract
├── runner.py              # CLI: submit/status/collect/list
├── jobs/                  # session-scoped job dirs (gitignored)
│   └── <session_id>/
│       └── <job_id>/
│           ├── job.lock   # cross-process file lock (msvcrt on Win)
│           ├── input.json # args + reader name
│           ├── output.json ← atomic write (.tmp → os.replace)
│           └── status.json ← atomic write
└── __init__.py            # marker
```

### C.2 Reader contract (Tier 1 — flash)

`runner.py submit --kind read --path <file> --reader flash`

Reader is a bounded file read: returns `{path, lines[range], sha256, captured_at}`. No model call needed — `runner.py` does it locally with atomic writes. The "brain" later can take the cached output.

### C.3 Brain contract (Tier 2 — planner, future)

`runner.py submit --kind brain --prompt <text> --files <paths...> --reader qwen-235b`

For now stub returns `status: brain_pending`. Later wiring calls DeepInfra `qwen-3-235b-a22b-instruct-2507` via `urllib.request` (stdlib only). Orchestrator polls `status` then `collect`s result.

### C.4 Concurrency safety

1. **Session isolation**: every job path includes `OPENCODE_SESSION_ID`. Runner refuses to operate if missing.
2. **Atomic writes**: every output file written as `<name>.tmp`, then `os.replace()` to final name. Prevents partial reads from other windows.
3. **Cross-process lock**: `msvcrt.locking` on `job.lock` (Windows; fall back to `fcntl.flock` on POSIX). Lock holds PID + timestamp.
4. **Stale lock cleanup**: lock older than `STALE_LOCK_MINUTES=30` AND holding PID not alive → safe to reclaim.
5. **Status enum**: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`.
6. **Never trust partial reads**: `collect` refuses to return output if `status.json` doesn't say `complete` or `stale_reclaimed`.

### C.5 Build steps

1. `write` `runner.py` (stdlib only: `os, sys, json, hashlib, time, pathlib, argparse, subprocess, msvcrt, urllib.request`).
2. `python -m py_compile .opencode/parallel/runner.py` to verify syntax.
3. Smoke test: `python -m runner submit --kind read --path README.md --reader flash` then `status <job_id>` then `collect <job_id>`.

---

## Part D — Pipeline Format Unification (extend "best format" to all pipelines)

### D.1 The reference format

`formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md` is the canonical "best format":
- Explicit metadata block (Date, Claim mode, Reference contract, Reference scope, Family archetype, Reference evidence, Official source, Concentration, Status)
- Concept Lock
- Formula table with columns: **# | Ingredient | Dilution | Amount (uL) | Active uL | Active ppm v/v proxy | Specific function**
- (Then pipeline analysis appends after a gate run)

### D.2 Pipelines to extend (must not require full main pipeline run)

1. `scripts/evaluate_formula.py` — add metadata-section parser; refuse to run unless `Claim mode` and `Reference contract` are present (or explicit "UNCLAIMED").
2. `scripts/oav_headspace_analyze.py` — emit a smaller JSON containing only the OAV table + note distribution; format the same way as `format_pipeline_analysis.py`.
3. `scripts/formula_simulator.py` — temporal evolution only; emit 5-window OAV; reuse `format_pipeline_analysis.py`'s `build_temporal` formatter.
4. `scripts/formula_diagnosis.py` — diagnostic-only; MUST emit a deviation report section if the formula header mentions a reference perfume (reuse my new `build_reference_deviation()`).
5. `scripts/formula_recommender.py` — pre-formulation recommendations only; must NOT touch the main pipeline.
6. `scripts/opus_v_workbook_pipeline.py` — workbook style; apply same metadata block requirement.

### D.3 Safeguards (anti-waste, anti-oversight)

1. **Refuse to gate any formula missing the metadata block**. `_gate_reference_claim_contract` already returns FAIL — wrap it with a hard preflight gate that refuses to run unless:
   - Either `Reference claim: none` is explicit, OR
   - All of `Claim mode`, `Reference contract`, `Reference scope` are present
2. **Refuse to gate if inventory stock contract has any UNRESOLVED issue**. Already a FAIL — promote to hard-block by adding a preflight wrapper.
3. **Refuse to run expensive pipelines if quantitative_authority is UNAVAILABLE**. Density fallback is a known blind spot for ppm w/w claims.
4. **Refuse to mix chemically incompatible naturals** (F11 lesson). Add a knowledge-graph check: any two complex naturals must share a chemical family marker.
5. **Pre-flight cost ticker**: emit `_ESTIMATED_MATERIAL_COST_THB` from known market prices in `data/thai_market_sales_2500_15000_thb.md` BEFORE running gates. Warn the user if the active mass value exceeds the typical retail bracket.

---

## Part E — Cache & Hook Strategy

### E.1 Local cache (free)

1. **Formula gate JSON outputs** → cache in `.opencode/cache/gate_results/<sha256_of_formula_txt_head>.json`. Reuse unless formula git HEAD changed.
2. **PubChem compound details** → cache in `.opencode/cache/pubchem/<cid>.json`. Use 30-day TTL.
3. **Reference contract evaluations** → cache by formula-name + git-sha of `reference_contracts.py`.

### E.2 Provider cache (paid but cheap)

1. DeepInfra supports prompt caching on `deepseek-v4-flash` ($0.018 vs $0.09). Pre-pend stable agent instructions before dynamic payload.
2. Afuture: DeepSeek API direct also supports context caching at 0.13x rate.

### E.3 Hooks

1. `tool.execute.before` for `read` of formula file → if stale local gate-cache exists and `_notes_shown`, reuse.
2. `tool.execute.after` for `write` to formula file → invalidate the gate cache for that formula.
3. Pre-bash hook: refuse `formula_release_gate.py` invocation if `OPENCODE_SESSION_ID` env is unset when more than 1 OpenCode window is open.

---

## Part F — Outstanding tasks from prior commands (carry-over checklist)

- [x] Set opencode.json `model` to `deepinfra/zai-org/GLM-5.2` (DONE earlier)
- [x] Set opencode.json `small_model` to `deepinfra/deepseek-v3.1` (DONE earlier)
- [x] Updated env-guard.js to forward 3 API keys + session id (DONE earlier)
- [x] Added `_note_overrides` marker about DeepLuna-Codex split (DONE earlier)
- [ ] Flip `enabled: true → false` on `deepluna_read` and `deepluna_fast_read` in opencode.json (Part B.2)
- [ ] Build `.opencode/parallel/runner.py` + README (Part C)
- [ ] Set `DEEPINFRA_SERVICE_TIER=priority` in env-guard.js (Part B.1)
- [ ] Run Part B.4 provider verification curls
- [ ] Extend D.2 pipelines with metadata-block requirement
- [ ] Add D.3 safeguard hard-blocks (mostly small preflight wrappers)
- [ ] Build E.1 local cache infrastructure

---

## Part G — Orchestrator handoff

### G.1 Recommended handoff

Hand to **myself (GLM-5.2 orchestrator)** at **priority tier**. Reasoning: this is the highest-leverage session, latency-critical for user. Use Sisyphus-Junior only for trivial leaf changes (category=quick) where GLM is overkill. Skip deep agent delegation (failed last attempt — governor auth).

### G.2 Execution order (tight)

1. B.2 (deepluna disable flag flip) — 2 minutes
2. B.1 (priority tier env) — 1 minute
3. C.5 (runner.py build + compile) — 15 minutes
4. B.4 (provider curls) — 2 minutes
5. D.3 safeguards (preflight wrappers) — 30 minutes
6. D.2 pipeline extensions — 60-90 minutes
7. E.1 cache scaffolding — 20 minutes

Total wall: ~2 hours, ~$2-4 in DeepInfra spend for orchestrator + 1 leaf task. Zero Codex DeepLuna spend.

### G.3 What this plan does NOT do

- Does NOT change Codex behavior — Codex config.toml untouched.
- Does NOT install plugins.
- Does NOT run the full main pipeline on any formula.
- Does NOT modify engine/ scientific modules (only scripts/ wrappers).
- Does NOT touch reference_contracts.py again (already extended this session).

---

**END OF PLAN v1 — review now, hand back to orchestrator on approval.**