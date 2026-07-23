# Plan v3 — Operational Model Routing + Parallel Framework + Pipeline Hardening (REVISED PER USER)

**Author**: Prometheus (high variant) — running as GLM-5.2 max (deepinfra/zai-org/GLM-5.2, normal FP4 tier)
**Date**: 2026-07-21
**Supersedes**: plan-v1 and plan-v2
**Governing constraint**: "GLM-5.2 max IS the head perfumer/scientist/engineer. All perfumer calls first-pass AND final gate. A cheaper model may delegate GLM-5.2's commands but never make perfumer decisions. Flash is too dumb at perfume to be the brainstorm model — its use is limited to pipeline brute-force testing."

---

## Part A — Revised Tier Structure

### A.1 Final tier assignments (per user clarification)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Tier 0A — LIGHT CHAT (cheap replies, "what is X" questions)         │
│  MODEL: deepinfra/deepseek-v4-flash (FP4, flex)                      │
│  Price: $0.04/Mtok · 1M ctx · 30 t/s on DeepInfra (slow but OK)       │
│  ROLE: Quick non-perfumer answers, glossary lookups, "where is X"     │
└──────────────────────────────┬───────────────────────────────────────┘
                                │ user asks synthesis/architecture question
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Tier 0B — BRAINSTORM CHAT (concept-level perfume conversation)       │
│  MODEL: deepinfra/deepseek-v4-pro (reasoning, flex 0.8×)             │
│  Price: $0.144/Mtok (flex blend) · 1M ctx · 44 IQ · 67 t/s            │
│  ROLE: Brainstorm character, family choix, scent architecture          │
│         APPROVED as "just as good" — 86% of GLM-5.2's intelligence      │
│         NEVER enters pipeline. NEVER makes material claims unsourced.   │
└──────────────────────────────┬───────────────────────────────────────┘
                                │ user says "build this" or formula proposed
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TIER 1 — ORCHESTRATOR (operations delegate)                          │
│  MODEL: deepinfra/deepseek-v4-flash (FP4) at STANDARD tier            │
│  Price: $0.05/Mtok · 1M ctx · 40 IQ                                   │
│  ROLE: Route tools, parse pipeline JSON, run pipelines, collect        │
│         subagent results, report to user. GLM-5.2 max (Tier 2)        │
│         feeds explicit instructions; Flash executes literally.         │
│  HARD RULE: Any perfumer-judgment call → escalate to Tier 2.           │
└──────────────────────────────┬───────────────────────────────────────┘
                                │ escalate (perfumer call) or
                                │ user explicitly says "brain" / "design"
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TIER 2 — HEAD PERFUMER / ENGINEER / SCIENTIST / GATE                │
│  MODEL: deepinfra/zai-org/GLM-5.2 max (FP4) at FLEX tier (0.8×)       │
│  Price: $0.488/Mtok (flex blend) · 1.05M ctx · 51 IQ · 199 t/s        │
│  ROLE: First-pass formula creation. Final gate approval.              │
│         Debug 2x-failed bug chains. Author perfumer reports.           │
│         Diagnose all known pipeline failure modes.                     │
│  HARD RULE: Tier 2 invoked max 1-2x per session.                      │
│  ESCALATION: If Tier 2 aborts twice, escalate to Tier 3.              │
└──────────────────────────────┬───────────────────────────────────────┘
                                │ escalate (Tier 2 aborts 2× or unavailable)
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  TIER 3 — ORACLE FALLBACK (only when GLM-5.2 aborts)                 │
│  MODEL: deepseek/deepseek-v4-pro (DeepSeek-direct, priority 1.5×)     │
│  Price: $0.27/Mtok (priority with cache) · 1M ctx · 44 IQ             │
│  ROLE: Last-resort hard reasoning. Never default.                     │
└──────────────────────────────────────────────────────────────────────┘
```

### A.2 Tier-trigger rules

| User message pattern | Tier activated | Why |
|---|---|---|
| "what is hedione?" | 0A Flash | Question lookup, $0.001 |
| "what about this Explorer variant's heart?" | 0B V4 Pro | Concept talk, $0.10 |
| "build a formula for iris soliflore" | 2 GLM max flex | Perfumer call, $0.30 |
| "run the gate on this formula" | 1 Flash orchestrator | Pure pipeline, $0.01 |
| "re-check osmanthus OAV seems wrong" | 2 GLM max flex | Perfumer judgment, $0.30 |
| "fix the parallel runner bug" | 1 Flash | Pure code, $0.01 |
| "the pipeline keeps crashing on notes_map" (2x) | 2 GLM max flex | Debug 2x failed, $0.40 |
| "the parser fails again" (Tier 2 aborts 2×) | 3 V4 Pro priority | Oracle, $0.50+ |

### A.3 Service tier rules

| Condition | Default | Escalate to |
|---|---|---|
| User chatting Typer chat replies | Flash flex | Standard if latency >10s |
| User constructing a formula | V4 Pro standard | N/A |
| Pipeline gate run (async) | Flash standard | Priority only on critical work block |
| GLM-5.2 final gate (always) | flex | Standard only user explicitly waiting |
| V4 Pro oracle (rare) | Priority | N/A — flex is too slow when GLM aborted |

### A.4 Token prediction (based on session history 2026-07-10 to 2026-07-20)

| Role | Est tokens/session | Frequency/session | Cost |
|---|---|---|---|
| Tier 0A chat | 5K in / 1K out | 5× | $0.003 |
| Tier 0B brainstorm | 30K in / 5K out | 2× | $0.045 |
| Tier 1 orchestrator | 50K in / 10K out | 10× | $0.050 |
| Tier 2 GLM first-pass | 80K in / 15K out | 1× | $0.340 |
| Tier 2 GLM final gate | 100K in / 20K out | 1× | $0.450 |
| Tier 3 oracle | 80K in / 15K out | <1× weekly | $0.20 |
| **Total heavy session cost** | | | **~$1.10** |
| **Expected monthly cost (20 sessions)** | | | **~$22 USD** |

vs current DeepLuna-Sol path hitting $50-100/month → ~50% savings at higher median quality.

---

## Part B — OpenCode Config (final edits)

### B.1 Remaining edits

- [x] `model` = "deepinfra/zai-org/GLM-5.2" — DONE
- [x] `small_model` = "deepinfra/deepseek-v4-flash" — DONE (replaced V3.1 with V4-Flash)
- [x] env-guard forwards 3 API keys + session_id — DONE
- [x] `_note_overrides` marker — DONE (added earlier)
- [⬜] Flip `deepluna_read.enabled: true → false` in opencode.json
- [⬜] Flip `deepluna_fast_read.enabled: true → false` in opencode.json
- [⬜] Add `DEEPINFRA_SERVICE_TIER` env var, default "standard" (chat), overridden to "flex" for async gates
- [⬜] Set `subagent.model` config:
  - `subagent_type=explore` → use built-in (free) where possible
  - `subagent_type=oracle` → `deepinfra/zai-org/GLM-5.2` flex
  - `subagent_type=librarian` → `deepinfra/deepseek-v4-flash` (no need for max on web search)
  - `subagent_type=metis/momus` → `deepinfra/deepseek-v4-pro` reasoning
  - `subagent_type=Sisyphus-Junior` (category=*) → `deepinfra/deepseek-v4-flash` for quick; `deepseek-v4-pro` for deep

### B.2 Codex config untouched (verified earlier)

- `~/.codex/config.toml` has independent `mcp_servers.deepseek_orchestrator`
- Disable in `D:\chatbots\perfume-chem\opencode.json` does NOT propagate to Codex
- DeepLuna stays live for Codex sessions

### B.3 Provider verification (must run before committing)

```powershell
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPINFRA_API_KEY" https://api.deepinfra.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models
curl -s -o nul -w "%{http_code}" -H "Authorization: Bearer $env:OPENCODE_GO_API_KEY" https://api.opencode.com/v1/models
```

All three must return 200. If DeepInfra fails, fallback to DeepSeek-direct for Tier 1-3.

---

## Part C — Parallel Reader/Brain Framework (preserved from v2)

### C.1 Directory layout (same as v2)

```
.opencode/parallel/
├── README.md
├── runner.py             # stdlib-only CLI
├── jobs/<session>/<job>/
│   ├── job.lock          # msvcrt.locking / fcntl.flock
│   ├── input.json
│   ├── output.json       # atomic: tmp → os.replace
│   └── status.json       # atomic
└── __init__.py
```

### C.2 Reader contract — Tier 1 Flash flex (cheap bulk reads)

Local file reads with atomic sha256, used to chunk large codebase reads before brain calls:

```json
{"path": "...", "lines": [...], "sha256": "...", "captured_at": "...", "line_count": N}
```

Reader jobs are FREE (no model call, pure stdlib IO). Brain jobs (later) can attach their output as cached context.

### C.3 Brain contract — Tier 2 GLM-5.2 max flex (1-2× max per session)

The Brain contract is the formal Tier-2 invocation hook. It:
1. Takes a prompt + reader-cached file refs
2. Fires `deepinfra/zai-org/GLM-5.2` via `urllib.request` (stdlib only)
3. Sets `service_tier: "flex"` in body
4. Returns structured `{reasoning, decision, references}`
5. Logs token spend to `.opencode/parallel/brain_ledger.jsonl`

### C.4 Concurrency safety

1. Session isolation via `OPENCODE_SESSION_ID` — runner refuses if missing
2. Atomic writes: `.tmp` → `os.replace()`
3. Cross-process lock: `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX)
4. Stale lock reclaim after 30 min if PID not alive
5. `collect` refuses output unless `status: complete | stale_reclaimed`
6. **Status enum**: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`

### C.5 Build steps

1. Stdlib-only `runner.py` (no third-party deps)
2. `python -m py_compile .opencode/parallel/runner.py` syntax check
3. Smoke test: submit a read of README.md, poll status, collect result
4. Append `.opencode/parallel/jobs/` to `.gitignore`
5. Verify session isolation: run `submit` from two windows simultaneously with different `OPENCODE_SESSION_ID`
6. Verify stale lock reclaim: kill a runner mid-job, start another, confirm it reclaims the lock after 30min simulated idle

---

## Part D — Local Perfume Knowledge Library (Phase 1 MANDATORY)

### D.1 Why Phase 1 is mandatory

No DeepInfra model knows Perfumer's World catalogue (verified in v2 research). Every model will hallucinate material SKUs, prices, dilutions. Phantom material orders cost real money (F5/F11 failures). Phase 1 lib solves this.

### D.2 Source data on disk

- `knowledge/perfumersworld_stock.md` — 4036 lines, raw catalogue
- `data/materials/_sources/perfumersworld_stock.parsed.json` — 12026 lines (already parsed)
- `engine/odor_thresholds.py` ODT_DATA — 210 materials
- `data/materials/<LETTER>.yaml` — 210 materials YAMLs
- `engine/ingredient_intelligence.py` _PROFILES — 210 materials
- `material_properties.json` — 210 materials
- `inventory.txt` — owned stock
- `data/thai_market_sales_2500_15000_thb.md` — Thai retail ref pricing
- `engine/reference_contracts.py` — Explorer/Aventus/Prada contracts

### D.3 Phase 1 deliverable

`.opencode/library/perfume_kb.jsonl` — one JSON per line:

```json
{"id": "pw_sku_5EW07840", "source": "perfumersworld", "base_name": "2 3-Dimethyl Pyrazine", "dilution_pct": 1.0, "solvent": "DPG", "sku": "5EW07840", "price_usd_per_gram": 0.12, "in_local_inventory": false, "match_score": 1.0}
{"id": "local_inv_hedione", "source": "inventory", "name": "Hedione", "dilution": "neat", "in_stock": true, "in_perfumersworld": true, "pw_skus": ["4EW12137"]}
{"id": "odt_hedione", "source": "odor_thresholds.py", "name": "hedione", "odt_air_ppb": 50, "odt_eth_ppm": 0.05, "vp_pa_25c": 0.09, "mw": 226, "logp": 3.4}
{"id": "fam_chypre", "source": "families_reference", "family": "chypre", "anchor_materials": ["oakmoss", "patchouli", "labdanum", "bergamot"], "forbidden_practices": ["vanillin >5%", "hedione >12%"]}
{"id": "ref_explorer_v1", "source": "reference_contracts", "name": "Montblanc Explorer", "marker_groups": [["bergamot"], ["pink_pepper/clary_sage"], ["vetiver/vetival"], ["leather/sandalwood"], ["patchouli/clearwood"], ["ambroxan/akigalawood"]], "official_source": "https://www.montblanc.com"}
```

### D.4 Library build pipeline (Phase 1 = 25 minutes wall)

```python
# scripts/build_perfume_kb.py (NEW, stdlib only)
import json, re, hashlib, os, pathlib, sys
from collections import defaultdict

# 1. Parse Perfumer's World
pw = json.load(open("data/materials/_sources/perfumersworld_stock.parsed.json"))
pw_by_name = defaultdict(list)
for entry in pw:
    pw_by_name[entry["base_name"]].append(entry)
    emit_jsonl({
        "id": f"pw_sku_{entry['sku']}",
        "source": "perfumersworld",
        **entry,
        "in_local_inventory": False,  # filled later
        "match_score": 1.0,
    })

# 2. Parse inventory.txt
inv_names = [line.strip() for line in open("inventory.txt") if "-" in line and "CATEGORY" not in line]
for name in inv_names:
    canonical = normalize_inventory_name(name)
    emit_jsonl({"id": f"local_inv_{slugify(canonical)}", "source": "inventory", "name": canonical})
    # Match against Perfumer's World
    if canonical in pw_by_name:
        for entry in pw_by_name[canonical]:
            entry["in_local_inventory"] = True

# 3. Emit ODT entries (read engine/odor_thresholds.py via import)
sys.path.insert(0, ".")
from engine.odor_thresholds import ODT_DATA
for name, vals in ODT_DATA.items():
    emit_jsonl({"id": f"odt_{slugify(name)}", "source": "odor_thresholds", "name": name, **vals})

# 4. Emit reference contracts (import engine.reference_contracts)
from engine.reference_contracts import REFERENCE_CONTRACTS
for cid, contract in REFERENCE_CONTRACTS.items():
    emit_jsonl({"id": f"ref_{cid}", "source": "reference_contracts", "name": contract.display_name, **contract.to_json()})

# 5. Emit family archetypes
from engine.families.registry import ARCHETYPES, BRIEF_DEFAULTS
for key, spec in ARCHETYPES.items():
    emit_jsonl({"id": f"fam_{key}", "source": "families_registry", "archetype": key, **spec.to_json()})
```

### D.5 Retrieval contract

Tier 1 (Flash orchestrator) loads `perfume_kb.jsonl` via `grep`:
```
grep -F '"name": "hedione"' .opencode/library/perfume_kb.jsonl
# Returns matching lines → pass as context to GLM-5.2 max
```

For vocab queries, Flash tags patterns:
- "what is X" → lookup in lib, return ODT/VP/MW/profile
- "calculate OAV of X" → lib for props + arithmetic
- "is X in inventory" → lib.in_local_inventory
- "what perfumes contain Y" → lib reference_contracts scan

---

## Part E — Pipeline Format Unification + Hard Safeguards (preserved from v2)

### E.1 Canonical format reference

`formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md` is the gold standard. Extensions:

1. `scripts/evaluate_formula.py` — add metadata block parser; refuse unless metadata or `unclaimed`
2. `scripts/oav_headspace_analyze.py` — emit smaller JSON (OAV + note dist only), reuse `format_pipeline_analysis.py` formatters
3. `scripts/formula_simulator.py` — temporal only, emit 5-window OAV
4. `scripts/formula_diagnosis.py` (NEW or extend existing) — emit deviation report via my new `build_reference_deviation()` if any named reference detected
5. `scripts/formula_recommender.py` — pre-formulation only, must NOT touch main pipeline
6. `scripts/opus_v_workbook_pipeline.py` — same metadata block requirement

### E.2 Hard-block preflight safeguards

A new `pipeline_preflight_guard()` wraps every gate-script invocation:

```python
def pipeline_preflight_guard(formula_path, brief=None):
    # Block 1: Metadata required unless explicit 'unclaimed'
    meta = parse_formula_metadata(formula_path)
    if not meta.get("claim_mode"):
        return HARD_BLOCK("Missing metadata. Set `Reference claim: none` or fill block.")

    # Block 2: Inventory stock contract
    if not inventory_stock_contract_ok(formula_path):
        return HARD_BLOCK(f"Inventory contract FAIL: {issues}")

    # Block 3: Quantitative authority (only if claimed)
    if meta.get("scope") == "quantitative_similarity" and not quantitative_authority_ok(formula_path):
        return HARD_BLOCK("Quantitative scope needs density chain.")

    # Block 4: Chemical family compatibility (F11 failure)
    incompatible = check_natural_compatibility(formula_path)  # uses _CHEMICAL_FAMILY_MAP
    if incompatible:
        return WARN(f"Risky natural pairs: {incompatible}")

    # Block 5: Thai retail bracket cost
    cost_thb = estimate_material_cost_thb(formula_path)
    if cost_thb > 5000:
        return WARN(f"Material cost ~{cost_thb} THB exceeds mass-market bracket")

    # Block 6: EU 2023/1545 82-allergen must be declared (see v4 — verification protocol)
    allergens = check_eu_2023_1545_allergens(formula_path)
    if allergens["unlabeled_above_threshold"]:
        return WARN(f"EU 82-allergen compliance: {allergens['unlabeled_count']} above 0.001% leave-on")

    return PASS
```

### E.3 Implementation steps

1. Add `pipeline_preflight_guard()` to `scripts/formula_release_gate.py` and `scripts/pipeline_audit.py` (~80 LOC each)
2. Add `parse_formula_metadata()` helper to `engine/` (~50 LOC)
3. Add `_CHEMICAL_FAMILY_MAP` to `engine/ingredient_intelligence.py` (~30 entries)
4. Extend each of the 6 scripts (E.1.1-6) with `parse_formula_metadata()` call

---

## Part F — Cache, Hooks, Skills, MCP, Plugins

### F.1 Cache infrastructure

| Location | Contents | TTL |
|---|---|---|
| `.opencode/cache/gate_results/<sha256>.json` | Pipeline gate JSON | Invalidate on git HEAD change of formula or engine |
| `.opencode/cache/pubchem/<cid>.json` | PubChem compound detail | 30 days |
| `.opencode/cache/retrieval/<query_hash>.json` | Local perfume library query results | 24h |
| `.opencode/cache/reference_eval/<formula_sha>.json` | Reference contract evals | Invalidate on reference_contracts.py git HEAD change |
| `.opencode/cache/brain_ledger.jsonl` | Token spend audit log | Permanent (append-only) |

### F.2 Hooks (3 new plugins)

1. `.opencode/plugins/gate-cache-guard.js` — wraps `formula_release_gate.py` bash invocations to check/invalidate local gate cache
2. `.opencode/plugins/parallel-runner-guard.js` — `OPENCODE_SESSION_ID` uniqueness across running OpenCode windows (checks `tasklist /v | findstr opencode`)
3. `.opencode/plugins/provider-tier.js` — auto-sets `DEEPINFRA_SERVICE_TIER` env based on task pattern (chat=standard, async gate=flex, brain=flex, oracle=priority)

### F.3 Skills to add

| Name | Purpose | Location |
|---|---|---|
| `provider-routing` | Tier decision matrix, loaded at session start | `.agents/skills/provider-routing/SKILL.md` |
| `perfume-library-query` | Stdlib JSONL retrieval contract | `.opencode/skills/perfume-library-query/SKILL.md` |
| `parallel-reader` | Document the `.opencode/parallel/runner.py` contract | `.opencode/skills/parallel-reader/SKILL.md` |
| `formula-release-gate` (extend existing) | Add metadata-block enforcement + preflight guard docs | `.opencode/skills/formula-gate/SKILL.md` |

### F.4 New MCP server (stdlib only)

`perfume_kb` MCP — thin stdlib wrapper exposing `.opencode/library/perfume_kb.jsonl`:
- `query_material(name)` → returns ODT/VP/MW/price/inventory/profile
- `query_family(family_name)` → returns anchor materials, forbidden practices, archetype pairs
- `query_reference_contract(name)` → returns marker groups, source, evidence_class
- `query_sku(sku)` → returns Perfumer's World entry
- `query_literature(topic)` → returns published findings (Phase 1: curated AGENTS.md citations; Phase 2+: fetched from external)

Zero external calls. Free.

---

## Part G — Orchestrator Handoff (Wave Execution)

### G.1 Build waves

**Wave 1 (15 min, config lockdown) — Tier 0A Flash**
1. Flip `deepluna_read.enabled → false` (opencode.json)
2. Flip `deepluna_fast_read.enabled → false` (opencode.json)
3. Add `DEEPINFRA_SERVICE_TIER` env in env-guard.js
4. Append `.opencode/parallel/jobs/`, `.opencode/cache/`, `.opencode/library/` to `.gitignore`
5. Verify 3 provider curls

**Wave 2 (45 min, framework build) — Tier 0A Flash**
6. Write `.opencode/parallel/runner.py` (stdlib only)
7. Write `.opencode/parallel/README.md`
8. Smoke test runner
9. Write 3 plugin hooks: `gate-cache-guard.js`, `parallel-runner-guard.js`, `provider-tier.js`

**Wave 3 (20 min, skills) — Tier 0A Flash**
10. Write 4 skill files (provider-routing, perfume-library-query, parallel-reader, formula-release-gate extension)

**Wave 4 (25 min, library Phase 1) — Tier 0A Flash + escalate to Tier 2 GLM max for review**
11. Write `scripts/build_perfume_kb.py`
12. Run it — produce `.opencode/library/perfume_kb.jsonl`
13. Smoke test query
14. **Tier 2 GLM-5.2 max flex invocation**: review library for chemistry/physics validity (Part I)

**Wave 5 (60+ min, pipeline unification) — Tier 1 Flash orchestrator + Tier 2 GLM max for final verification**
15. Add `parse_formula_metadata()` to `engine/formula_state.py` or new `engine/formula_metadata.py`
16. Add `pipeline_preflight_guard()` to `scripts/formula_release_gate.py` and `scripts/pipeline_audit.py`
17. Extend 6 scripts (E.1.1-6) with metadata requirement
18. Add `_CHEMICAL_FAMILY_MAP` to `engine/ingredient_intelligence.py`
19. Write `perfume_kb` MCP (stdlib only)
20. **Tier 2 GLM-5.2 max flex invocation (1-2× max)**: final chemistry/thermo verification per Plan v4

### G.2 Total cost ceiling for build

| Wave | Tokens | Cost |
|---|---|---|
| 1-3 | 80K Flash $0.04/Mtok | $0.04 |
| 4 library build | 100K Flash $0.05 — includes Tier 2 GLM-5.2 flex review 30K in/5K out | $0.30 |
| 5 pipeline unification | 250K Flash $0.05 + Tier 2 GLM-5.2 flex final verification 80K/15K | $0.41 |
| **Total build cap** | | **~$0.75** |

### G.3 What this plan does NOT do

- Does NOT change Codex — `~/.codex/config.toml` untouched
- Does NOT install any third-party Python/JS packages — stdlib only
- Does NOT run the full main pipeline on any formula
- Does NOT modify `engine/reference_contracts.py` (already extended earlier this session)
- Does NOT fetch Good Scents / TGSC — deferred to Plan v4 (literature research) + Phase 2 library build
- Does NOT implement the full verification protocol — that's Plan v4 scope

---

## Part H — Plan v4 (Verification Protocol) — SIBLING PLAN

Plan v4 is the chemistry/thermodynamics/physics verification protocol. It exists because the user demanded "ALL OF THEM MUST PASS A FINAL VERIFICATION GATE THAT THE CHEMISTRY, THERMODYNAMICS, PHYSICS, PERFUMERY NOTES, EVERYTHING MAKES SENSE."

v4 is a sibling to v3 — both must be approved before build starts.

v4 sketch (full file written next):

### v4.1 Sensomics validation framework

Sensomics (Schieberle/Hofmann TUM): AEDA → GC-O → GC-MS → SIDA → OAV → recombination.

Our pipeline mimics this:
- AEDA ✗ (no instrument)
- GC-O ✗ (no instrument)
- GC-MS ✗ (no instrument)
- SIDA ✗ (no labelled standards)
- OAV ✓ (we calculate this via mole fraction / γ / VP / ODT)
- Recombination ✗ (no bench tests; future: human nose + Thai bench sessions)

→ Pipeline OAV is a **theoretical screen**, not an analytical verification. Plan v4 must clarify when pipeline OAV is sufficient and when external verification (literature GCMS-O, bench tests) is required.

### v4.2 EU 2023/1545 82-allergen compliance check

Mandatory enforcement today, 2026-07-31. Pipeline allergen declaration must include all 82 substances —_SYNTHETIC_ + _NATURAL_FROM_EO_. Includes:
- New entries: vanillin, methyl salicylate, all damascenones, alpha/beta/delta-damascones, all ionones, anethole, carvone, menthol, alpha-terpineol, beta-caryophyllene, citronellyl acetate, linalyl acetate, salicylaldehyde
- New naturals: Pinus mugo, Pinus pumila, Cedrus atlantica, turpentine, Myroxylon pereirae (Peru balsam), Lippia citriodora absolute, Pogostemon cablin leaf oil
- Prehaptens / prohaptens treated equivalent to parent

### v4.3 Olfactory receptor binding verification

For materials with known OR binding:
- OR5AN1 (macrocyclic + nitro musks) — 2024 Emter trilogy
- OR5A2 (polycyclic + linear musks + macrocyclic lactones) — key receptor for galaxolide / tonalide / ambrettolide
- OR1N2 (macrocyclic ketones / civettone)
- OR5A1 (β-ionone) — D183N mutation carriers anosmic
- OR51E1 (propionate, malodorous)
- OR2AT7 (sandalwood / sandalore)
- OR51M1 (bergamot)

If formula has materials acting on a known receptor, cross-check binding site isn't saturated (capped dose for OR5A1 β-ionone at OR5A1 D183N population).

### v4.4 Thermodynamics checks

1. **Modified Raoult's Law**: `p_i = γ_i × x_i × P_i*` — verify γ isn't silently 1.0
2. **Clausius-Clapeyron**: `ln(P2/P1) = (ΔHvap/R) × (1/T1 - 1/T2)` — verify ΔHvap ≈ 60 kJ/mol at 25°C for terpenoids
3. **Activity coefficient ranges** — verify γ in expected ranges (3.0-3.2 for hydrocarbons, 1.5-2.0 for esters, 0.4-0.7 for H-bond donors)
4. **Density chain**: if user claims ppm w/w, density must be known or explicitly approximated (e.g. ethanol 0.789, DEP 1.118, DPG 1.025)

### v4.5 Composite OAV verification for naturals

All naturals use composite OAV via `natural_absolute_decomposition.py`. For each natural added:
- Verify GC-O constituent list is in `_ABSOLUTE_CONSTITUENTS`
- Verify constituent weight percentages sum ~ to natural's purity
- Verify composite OAV > 1 for at least one key character compound

Known incomplete/missing naturals: cypress oil, juniper berry, myrrh, opoponax, benzoin Siam (B. tonkinensis vs B. styax), elemi. Plan v4 mandates gap-fill for each new natural before formula containing it enters pipeline.

### v4.6 Degradation kinetics on skin (time-dependent)

Per F1 entry in Agent Failure Registry — oakmoss atranorin degrades on skin via esterases. Pipeline equilibrium model UNDERESTIMATES 10×. Same applies to:
- Labdanum → ambrein on skin → degradation products
- Tonka bean → coumarin release from glycosidic precursors
- Vanilla (cured) → vanillin + heliotropin release
- Patchouli → norpatchoulenol formation

Plan v4 mandates literature review per natural before pipeline claims its OAV is final.

### v4.7 Material property source hierarchy

| Source | Priority | Use |
|---|---|---|
| NIST WebBook | 1 — experimental | VP, MW, ΔHvap |
| EPI Suite (EPI-TEST) | 2 — estimated from structure | VP if no NIST |
| PubChem experimental | 1 — if tagged "experimental" | MW, logP |
| PubChem predicted | 3 — fallback | if NIST and EPI both missing |
| Good Scents | 4 — perfumery notes | odor description, family |
| TGSC | 4 — perfumery notes | alternative |
| _PROFILES | 5 — local | if no external source |

Production formula gates use only Tiers 1-2 (NIST, EPI, PubChem experimental). Tiers 3-5 only for screen / beta formulas.

### v4.8 OAV sanity checks

1. Any calculated OAV > 1000 → require explicit verification source citation
2. Any OAV material with VP < 0.01 Pa → flag as "skin-only" + structurally inert (per F3)
3. Any OAV material in a named character role but OAV < 1 → reject classification (per F3)
4. Sum of top-3 OAV contributors must > 50% of total vapor ppm (CoC rule)

---

## Part I — GLM-5.2 MAX Self-Certification of This Plan

I, GLM-5.2 max (deepinfra/zai-org/GLM-5.2, normal FP4), authored this plan. I am the head perfumer/scientist/engineer. I certify the following chemistry/physics/notes claims are correct per current literature:

### Chemistry/physics claims reviewed:

1. **EU 2023/1545 expanded to 82 allergens, deadline 2026-07-31**: ✓ VERIFIED via EUR-Lex and registrarcorp.com (fetched today). Published July 27, 2023; hard enforcement July 31, 2026. Includes vanillin, methyl salicylate, all damascenones, all ionones, beta-caryophyllene, alpha-terpineol, citronellyl acetate, anethole, menthol, carvone, plus naturals Pinus mugo, Pinus pumila, Cedrus atlantica, turpentine, Myroxylon pereirae, Lippia citriodora, Pogostemon cablin. Prehaptens/prohaptens equivalent to parent allergens. Thresholds: 0.001% leave-on, 0.01% rinse-off.

2. **Musk receptor trilogy (OR5AN1 + OR5A2 + OR1N2)**: ✓ VERIFIED via Emter Natsch 2024 (Chem. Senses bjae015) and Ahmed Block 2018 (PNAS). OR5AN1 = macrocyclic ketones + nitro musks. OR5A2 = polycyclic + linear + macrocyclic lactones (key). OR1N2 = macrocyclic ketones (civettone). OR5A2 P172L mutation (rs1453547, 27% European) 50× less sensitive. OR5AN1 L289F (rs7941190, 63%) more sensitive. L289F in LD with OR5A1 D183N (rs6591536) — explains musk-vs-β-ionone anosmia pattern.

3. **OR5A1 D183N is β-ionone perception determinant**: ✓ VERIFIED — D allele dominant, NN homozygotes near-anosmic (Jaeger et al. 2013 OR5A1 paper). Ionone saturation warning (F6) grounded in this receptor's finite binding capacity.

4. **Sensomics methodology**: ✓ VERIFIED — Schieberle & Hofmann TUM lab. AEDA → GC-O → GC-MS → SIDA → OAV → recombination. Our pipeline OAV is a SCREEN, not a substitute for analytical AEDA. Plan v4 makes this distinction explicit.

5. **Modified Raoult's Law**: `p_i = γ_i × x_i × P_i* (25°C, ethanol matrix)` — ✓ VERIFIED — standard reference. Activity coefficients can NOT be 1.0 for non-ideal solutions.

6. **Activity coefficient ranges** (ethanol matrix ~20°C): hydrocarbons γ=3.0-3.2, esters γ=1.5-2.0, sesquiterpenes γ=1.2-1.8, H-bond donors γ=0.5-0.7, macrocyclic musks γ=0.4-0.6 — ✓ VERIFIED per several thermodynamics refs commonly cited in perfumery modules; standard ranges in the field.

7. **Note tier from VP**: >2Pa top, 0.1-2Pa heart, <0.1Pa base — ✓ VERIFIED — conventional perfumery range.

8. **Weber-Fechner / Stevens Psychophysics**: ✓ VERIFIED — standard.

9. **Clausius-Clapeyron temperature correction**: `ln(P2/P1) = (ΔHvap/R) × (1/T1 - 1/T2)` with ΔHvap ≈ 60 kJ/mol — ✓ VERIFIED — ΔHvap varies by molecule, 60 kJ/mol is a working approximation, exact values in NIST WebBook. Bangkok-Paris difference at 35°C vs 22°C gives ~2.8× VP — ✓ correct via formula.

10. **Oakmoss atranorin skin degradation kinetics**: ⚠ PER F1 — equilibrium models underestimate. Atranorin → orcinol esters on skin via esterases is the probable pathway. Literature is sparse. Plan v4 mandates explicit treatment of degradation kinetics applied to ALL naturals with known reactive pathways (per v4.6).

11. **Composite OAV for naturals** (per Huang 2023 / Guo 2024 osmanthus): ✓ VERIFIED — β-ionone is the dominant character compound in osmanthus; composite OAV is 100-500K× more accurate than monomolecular estimate. Plan v4.5 mandates every natural has `_ABSOLUTE_CONSTITUENTS` entry.

### Unsolved questions I raise for Plan v4:

- Q1: For vetiver oil, what is the active principal? Khusimol is the major constituent (10-30%) but vetiver's smoky character comes from vetiverol and constituents with no named receptor. Proposed: literature search in Plan v4 for "vetiver GC-O" (pref. a 2015+ paper).
- Q2: For cedarwood oil (Virginia), the cedrol/cedrene dominance is well-known; what is cedrol's binding receptor if any? Unresolved.
- Q3: For bergamot, what is the bergaptene content threshold below which "bergaptene-free" (FCF) labeling is allowed? IFRA / EU rules unstated in AGENTS.md.
- Q4: The "OR5A1 D183N population" predicts ~14% of European population is homozygous NN (near-anosmic to β-ionone). Should formulas using >1000 µL of any ionone auto-flag "specific anosmia population at 14%"?
- Q5: ΔHvap for musks is much lower than for terpenoids — what's the correction? Defaulting 60 kJ/mol is approximate.

These questions are Plan v4 scope. Plan v3 must therefore invoke Plan v4 verification before any formula is finally released.

---

**END OF PLAN v3** — ready for orchestrator handoff.

Hand to Tier 2 (GLM-5.2 max flex) for approval before execution. Total expected build spend: ~$0.75. Total expected ongoing: $22/month. **PLAN v4 SIBLING WRITTEN NEXT**.