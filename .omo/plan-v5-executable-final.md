# Plan v5 — Executable Final (Revisions Locked by User 2026-07-21)

**Supersedes**: v1, v2, v3, v4 (these are retained as research/literature archives)
**Status**: APPROVED FOR EXECUTION via `/start-work`
**Author**: Prometheus (high variant) running as GLM-5.2 max
**Date**: 2026-07-21

---

## User-Locked Revisions (binding on orchestrator)

1. **Tier 0A (Light chat)**: `deepinfra/deepseek-v4-flash` — OK for "what is X" questions and **pipeline brute-force testing** (user explicit)
2. **Tier 0B (Brainstorm chat)**: `deepinfra/deepseek-v4-pro` — "just as good" floor for concept-level perfume talk; Flash explicitly OUT of perfumer-brain work ("Flash is a shit model that gets perfumes wrong")
3. **Tier 1 (Orchestrator)**: `deepinfra/deepseek-v4-flash` — pure delegation, executes GLM-5.2 max's commands literally
4. **Tier 2 (Head perfumer/scientist/engineer/final gate)**: `deepinfra/zai-org/GLM-5.2` max — first-pass formula creation + final gate approval, invoked 1-2× max per session, **FLEX tier (0.8×)** per user directive
5. **Tier 3 (Oracle fallback)**: `deepseek/deepseek-v4-pro` DeepSeek-direct, priority tier — only when Tier 2 aborts 2×
6. **Allergens / phototoxicity / skin sensitization are NOT hard blocks.** They are WARNs. Pipeline auto-recommends Perfumer's World substitutes AND/OR emits two alternative formula versions using inventory materials.
7. **Oakmoss CoA gate: DENIED.** Do not require supplier atranol/chloroatranol CoA document from user. Oakmoss gate runs as WARN only.
8. **GLM-5.2 self-certification in Plans v3/v4 Part I/M is APPROVED.**
9. **Plan v4 Phase 1 Perfumer's World → JSONL library build: MANDATORY.**

---

## Execution Waves (total cap ~$1.57)

### Wave 1 — Config lockdown (15 min, Tier 0A Flash)

Todos for orchestrator:
- [ ] Fix JSON syntax error in `opencode.json` — remove invalid `_note_overrides` key from inside `permission` object (not a legal JSON key). Move the note to a comment elsewhere (e.g. `instructions` array) or drop it.
- [ ] Flip `deepluna_read.enabled: true → false` (search for the MCP server block in opencode.json)
- [ ] Flip `deepluna_fast_read.enabled: true → false`
- [ ] Add `DEEPINFRA_SERVICE_TIER` env passthrough in `.opencode/plugins/env-guard.js` (default "standard", overridable per process)
- [ ] Append `.opencode/parallel/jobs/`, `.opencode/cache/`, `.opencode/library/` to `.gitignore`
- [ ] Run provider verification curls (DeepInfra, DeepSeek, OpenCode Go) — all should return 200
- [ ] Verify `~/.codex/config.toml` is untouched (Codex keeps DeepLuna)

### Wave 2 — Parallel reader/brain framework (45 min, Tier 0A Flash)

Todos:
- [ ] Create `.opencode/parallel/runner.py` — stdlib only (os, sys, json, hashlib, time, pathlib, argparse, subprocess, msvcrt, urllib.request, urllib.error)
- [ ] Implement submit/status/collect/list/cleanup CLI subcommands
- [ ] Session isolation via `OPENCODE_SESSION_ID` env (refuse if missing)
- [ ] Atomic writes via `.tmp` → `os.replace()`
- [ ] Cross-process file lock via `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX)
- [ ] Stale lock reclaim after 30 min if holding PID no longer alive
- [ ] Status enum: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`
- [ ] Create `.opencode/parallel/README.md` (≤50 lines, contract + usage)
- [ ] Create empty `.opencode/parallel/__init__.py`
- [ ] Verify `python -m py_compile .opencode/parallel/runner.py`
- [ ] Smoke test: `python -m runner submit --kind read --path README.md --reader flash`
- [ ] Write 3 plugin hooks:
  - `.opencode/plugins/gate-cache-guard.js`
  - `.opencode/plugins/parallel-runner-guard.js`
  - `.opencode/plugins/provider-tier.js`

### Wave 3 — Skills (20 min, Tier 0A Flash)

Todos:
- [ ] Write `.agents/skills/provider-routing/SKILL.md` (tier decision matrix, loaded at session start)
- [ ] Write `.opencode/skills/perfume-library-query/SKILL.md` (JSONL retrieval contract)
- [ ] Write `.opencode/skills/parallel-reader/SKILL.md` (runner.py contract)
- [ ] Extend `.opencode/skills/formula-gate/SKILL.md` with metadata-block enforcement + preflight guard docs

### Wave 4 — Perfume library Phase 1 (25 min, Tier 0A Flash + Tier 2 GLM max flex review)

Todos:
- [ ] Write `scripts/build_perfume_kb.py` (stdlib only)
- [ ] Parse `data/materials/_sources/perfumersworld_stock.parsed.json` → emit `pw_sku_*` entries
- [ ] Parse `inventory.txt` → emit `local_inv_*` entries + set `in_local_inventory=true` on matching PW entries
- [ ] Parse `engine/odor_thresholds.py` ODT_DATA → emit `odt_*` entries
- [ ] Parse `engine/reference_contracts.py` REFERENCE_CONTRACTS → emit `ref_*` entries
- [ ] Parse `engine/families/registry.py` ARCHETYPES → emit `fam_*` entries
- [ ] Output all to `.opencode/library/perfume_kb.jsonl` (one JSON per line)
- [ ] Smoke test: `grep -F '"name": "hedione"' .opencode/library/perfume_kb.jsonl` returns matching lines
- [ ] **Tier 2 GLM-5.2 max flex invocation 1 of 1**: review library for chemistry/physics validity (per Plan v4 Part I certification)

### Wave 5 — Pipeline preflight + format unification (60-90 min, Tier 1 Flash orchestrator + Tier 2 GLM max final verification)

Todos:
- [ ] Add `parse_formula_metadata()` helper to `engine/formula_state.py` or new `engine/formula_metadata.py` (~50 LOC)
- [ ] Add `pipeline_preflight_guard()` to `scripts/formula_release_gate.py` and `scripts/pipeline_audit.py` (~80 LOC each)
  - Block 1: Metadata required unless explicit `Reference claim: none`
  - Block 2: Inventory stock contract
  - Block 3: Quantitative authority (only if claimed)
  - Block 4: Chemical family compatibility (F11)
  - Block 5: Thai retail bracket cost
  - Block 6: EU 2023/1545 82-allergen WARN (NOT hard block — per user)
- [ ] Add `_CHEMICAL_FAMILY_MAP` to `engine/ingredient_intelligence.py` (~30 entries)
- [ ] Extend 6 scripts with metadata-block parsing:
  1. `scripts/evaluate_formula.py`
  2. `scripts/oav_headspace_analyze.py`
  3. `scripts/formula_simulator.py`
  4. `scripts/formula_diagnosis.py`
  5. `scripts/formula_recommender.py`
  6. `scripts/opus_v_workbook_pipeline.py`
- [ ] Write `perfume_kb` MCP (stdlib only, exposes query_material / query_family / query_reference_contract / query_sku)
- [ ] **Tier 2 GLM-5.2 max flex invocation 2 of 2**: final chemistry/thermo verification per Plan v4 (Part K)

### Wave 6 — Literature citations database (15 min, Tier 1 Flash)

Todos:
- [ ] Write `.opencode/library/citations.jsonl` from Plan v4 Part L (40 entries)
- [ ] Write `.opencode/library/eu_2023_1545_allergens.json` (82 entries with INCI + CAS + threshold)
- [ ] Write `.opencode/library/phototoxic_oils.json` (Part D.2 entries)

### Wave 7 — Verification protocol (90 min, Tier 1 + escalate to Tier 2 GLM max)

Todos:
- [ ] Write `scripts/verify_formula_protocol.py` (NEW) reading pipeline JSON + formula markdown
- [ ] Implement verification categories A.1-A.10 (per Plan v4)
- [ ] **A.2/A.3/A.6 are WARN, NOT hard blocks** (per user-locked revision #6)
- [ ] A.2 allergen WARN: when allergen >0.001% leave-on / 0.01% rinse-off, auto-lookup Perfumer's World substitute in same chemical class/role and emit suggestion in message
- [ ] A.3 phototoxicity WARN: when bergamot regular >0.4% leave-on, auto-recommend FCF equivalent PW SKU + generate v2 formula with FCF substitution
- [ ] A.6 oakmoss skin sensitization WARN (NOT hard block per revision #7): flag "contains oakmoss absolute — atranol+chloroatranol <100 ppm supplier CoA recommended" but allow pipeline run; if >IFRA limit, recommend Evernyl (oakmoss substitute) PW SKU substitution
- [ ] For every WARN with a substitution suggestion: if formula contains inventory material that violates AND a PW substitute exists → emit TWO versions (original + alternative) using inventory-compatible substitutes
- [ ] Test on 2 existing formulas (Osmanthus Explorer, Prada L'Homme)
- [ ] **Tier 2 GLM-5.2 max flex review**: confirm script matches protocol

### Wave 8 — Pipeline integration (60 min, Tier 1 orchestrator)

Todos:
- [ ] Add `verify_formula_protocol` as new pipeline gate in `engine/pipeline/gates.py` (status: PASS/WARN, never FAIL for A.2/A.3/A.6 per user)
- [ ] Add `vp_source` field to `data/materials/<LETTER>.yaml` schema — audit 210 materials for Tier 1-2 NIST/EPI/PubChem_exp sources first
- [ ] Add `_CHARACTER_IMPACT_BONUS` to `engine/pipeline/natural_absolute_decomposition.py`:
  - Vetiver: α-vetivone 5×, β-vetivone 5×, khusimone 20× (per Belhassen 2014 + Adams 2014 + Pandey 2024)
  - Osmanthus: β-ionone 5× (per Hong 2023 + Guo 2024)
  - Cedarwood Virginia: α-cedrene 5×, cis-thujopsene 3× (per Setzer 2026 + Woo 2017 OR10J5)
  - Oakmoss: methyl atratate 3×, methyl-β-orcinol-carboxylate 3× (per Joulain 2009 + Bouges 2018)
- [ ] Audit `_ABSOLUTE_CONSTITUENTS` — flag naturals with constituent sum <30% as incomplete
- [ ] Add EU 2023/1545 82-allergen check to existing `safety_ifra_allergen` gate (extend list 26 → 82, threshold downgrade FAIL → WARN per user)
- [ ] Add phototoxicity check as new gate `safety_phototoxic_furanocoumarin` (WARN only)
- [ ] Add receptor saturation check `safety_receptor_saturation` (WARN only, per Plan v4 Part E)
- [ ] **Tier 2 GLM-5.2 max flex final verification**: run on Osmanthus Explorer — confirm all gates pass (with WARNs where expected)

---

## Disposition of Original Plan v4 Hard-Block Categories (Per User)

| Category | Original Plan v4 | LOCKED Behavior |
|---|---|---|
| A.1 OAV physics | Hard block on γ=1.0 / wrong VP source | **Hard block** (per physics, not safety) |
| A.2 EU allergens | Hard block | **WARN with PW substitute suggestion** + emit alternative formula version |
| A.3 Phototoxicity | Hard block | **WARN with PW substitute suggestion** (e.g. FCF bergamot) + emit v2 formula |
| A.3 quant authority | Hard block (if claimed) | **Hard block** (not safety — quantitative claim integrity) |
| A.4 Receptor saturation | Soft guideline | **WARN** (per original Plan v4) |
| A.5 Composite OAV | Hard block if natural missing | **WARN** + suggest in-inventory closest substitute from PW catalog |
| A.6 Oakmoss CoA | Hard block | **DENIED — WARN only, no CoA required**. If atranol+chloroatranol >IFRA limit, recommend Evernyl substitution. |
| A.7 VP source | Hard block | **Hard block** for production-release claim; WARN for draft |
| A.8 Sensomics disclaimer | Manual gate | **Always append disclaimer text** to released formula markdown |
| inventory_stock_contract | Hard block | **Hard block** (no inventory = no mix possible) |
| quantitative_authority | Hard block | **Hard block** (claim integrity) |

---

## Auto-Substitution Engine (NEW per user revision #6)

### Behavior

When any of A.2/A.3/A.6 raises a WARN:

1. Read the offending material(s) from `formula_state`
2. Look up the material in `.opencode/library/perfume_kb.jsonl`:
   - Get the material's chemical class / role / function
   - Get Perfumer's World SKUs in the same class/role (e.g. all "bergamot" variants with FCF marker, all "oakmoss substitutes" like Evernyl)
3. Filter by what's in the local inventory (if any) — prefer inventory first
4. If inventory has a substitute: emit "Version A (inventory-only)" formula
5. If PW has a substitute but inventory doesn't: emit "Version B (purchase required)" formula with projected cost delta in THB / USD
6. Output to user as:
   ```
   ⚠️ A.2 WARN: Bergamot EO at 0.6% exceeds IFRA 0.4% leave-on limit.
   Recommended substitutions (shared chemical class: citrus-bergamot):
     [INVENTORY] Bergamot FCF Sicilian — available @ 50 µL active, raises cost ~$0.02/30mL
     [PW PURCHASE] Bergamot FCF (5EW12137) — $0.45/g, not in inventory
   Generated 2 alternative formula variants:
     v_inventory.md → swaps Bergamot EO → Bergamot FCF Sicilian
     v_pw_purchase.md → swaps Bergamot EO → Bergamot FCF (5EW12137) @ $0.45/g
   ```

### Implementation

- New function `recommend_substitutes(material_name, violation_type, perfumers_world_json, inventory)` in `scripts/verify_formula_protocol.py`
- Substitute map built from PW `.opencode/library/perfume_kb.jsonl` entries:
  - Group PW SKUs by `base_name` (all dilutions/variations of same material)
  - Group by chemical class (substitutability)
  - Cross-reference with local inventory for cost-aware ranking

---

## Files To Create (build manifest)

### `.opencode/parallel/`
- README.md
- runner.py
- __init__.py

### `.opencode/plugins/` (3 new)
- gate-cache-guard.js
- parallel-runner-guard.js
- provider-tier.js

### `.agents/skills/` (1 new)
- provider-routing/SKILL.md

### `.opencode/skills/` (3 new/extended)
- perfume-library-query/SKILL.md
- parallel-reader/SKILL.md
- formula-gate/SKILL.md (extend)

### `.opencode/library/` (4 new)
- perfume_kb.jsonl (built by `scripts/build_perfume_kb.py`)
- citations.jsonl
- eu_2023_1545_allergens.json
- phototoxic_oils.json

### `.opencode/cache/` (created, gitignored)
- gate_results/
- pubchem/
- retrieval/
- reference_eval/
- brain_ledger.jsonl

### `scripts/` (3 new)
- build_perfume_kb.py
- verify_formula_protocol.py
- mcp_perfume_kb.py (or wherever the stdlib MCP lives)

### `engine/` (4 modifications)
- pipeline/gates.py (add verify_formula_protocol gate + extend safety_ifra_allergen + add safety_phototoxic_furanocoumarin + add safety_receptor_saturation)
- pipeline/natural_absolute_decomposition.py (add _CHARACTER_IMPACT_BONUS for vetiver/osmanthus/cedarwood/oakmoss)
- ingredient_intelligence.py (add _CHEMICAL_FAMILY_MAP)
- formula_state.py or new formula_metadata.py (add parse_formula_metadata)

### `scripts/` (6 modifications)
- formula_release_gate.py (add pipeline_preflight_guard)
- pipeline_audit.py (add pipeline_preflight_guard)
- evaluate_formula.py (add metadata block requirement)
- oav_headspace_analyze.py (reuse formatters; emit smaller JSON)
- formula_simulator.py (emit 5-window OAV only)
- formula_diagnosis.py or new (emit deviation report)
- formula_recommender.py (pre-formulation only)
- opus_v_workbook_pipeline.py (metadata requirement)

### Configuration
- opencode.json (fix JSON syntax error from earlier edit, flip deepluna MCP server `enabled: false`)

### `.gitignore` (1 modification)
- Append `.opencode/parallel/jobs/`, `.opencode/cache/`, `.opencode/library/`

---

## Cost Summary

| Wave | Tier | Tokens | Cost (USD) |
|---|---|---|---|
| 1 (config) | 0A Flash | 50K in / 10K out | $0.003 |
| 2 (framework) | 0A Flash | 80K in / 20K out | $0.005 |
| 3 (skills) | 0A Flash | 60K in / 15K out | $0.005 |
| 4 (library) | Flash + Tier 2 GLM max 30K/5K review | ~150K total | $0.29 |
| 5 (pipeline unification) | Flash + Tier 2 GLM max 80K/15K | 330K | $0.41 |
| 6 (citations db) | Flash | 100K | $0.005 |
| 7 (verify script) | Flash + Tier 2 GLM max 50K/10K | 260K | $0.25 |
| 8 (pipeline integration) | Flash + Tier 2 GLM max 50K/10K | 300K | $0.30 |
| **Total build cap** | | | **~$1.30** (revised from $1.57 — sans oakmoss CoA gate work) |

### Monthly recurring (post-build)

- Base operating per Plan v3: $22/month
- Verification protocol overhead per Plan v4 Wave: ~$1.30/month
- Auto-substitution engine query: ~$0.50/month (PW lookups are cheap)
- **Total: ~$23.80/month**

---

## Approval & Sign-off (locked by user)

- [x] User approved tier structure (revisions 1-5 from final user message)
- [x] User approved Phase 1 Perfumer's World library (revision 9)
- [x] User denied oakmoss CoA gate (revision 7)
- [x] User converted A.2/A.3/A.6 hard blocks to WARNs with auto-substitution (revision 6)
- [x] GLM-5.2 max self-certification of chemistry/thermo/physics/notes accepted (revision 8)
- [x] Orchestrator = user (me, GLM-5.2 max normal FP4)
- [x] Hand off via `/start-work` to execute the waves

**Total expected: ~$1.30 build, ~$24/month ongoing.**

---

## Plan complete. Ready for `/start-work`.

**Implementation owner**: GLM-5.2 max orchestrator (me, this session) operating under ulw-plan sticky rules — when `/start-work` fires, orchestrator executes wave-by-wave, escalating to Tier 2 GLM-5.2 max flex sign-off at designated checkpoints.

**Codex DeepLuna**: untouched remain active.

**Do NOT execute yet. Await user `/start-work` command.**