# Plan v5-R (Replan, rev 3) — Consolidate, Verify, Close, Remediate

**Origin**: `.omo/plan-v5-executable-final.md` (Prometheus / GLM-5.2 max, 2026-07-21)
**rev 3 change**: incorporates DeepSeek parallel delegation strategy (per user request) for the remaining googlework. A3 is now ~96% done (12/16 typing bugs fixed; 4 remain in one file). All other Phase A gates pending.

---

## Execution state as of this plan submission

| Gate | Status | Evidence |
|---|---|---|
| A0 — Deepluna guard | ✅ PASS | no `deepluna` in opencode.json |
| A1 — py_compile 16 new modules | ✅ PASS | re-verified after edits; all 16 compile |
| A2 — ruff regression | ✅ PASS | re-verified; 0 errors engine/ scripts/ tests/ validate/verify |
| A3 — basedpyright on 16 new modules | 🟡 4/16 errors remain | 12 fixed across `solvent_matrix.py`, `formula_metadata.py`, `kb_migrate.py`, `reference_contracts.py`, `build_perfume_kb.py`; 4 remain in `scripts/verify_formula_protocol.py:308,311,313,314` |
| A6a — Hedione in perfume_kb | ✅ PASS | 1 matching entry |
| A6b — 5 KB sources present | ✅ PASS | 1932 entries; sources = perfumersworld/local_inventory/odt_data/reference_contracts/families_registry |
| A6c — EU allergens length | ✅ PASS | exactly 82 |
| A4, A5, A7, A8, A9, A10 | ⏳ pending | |
| B1–B4, C1–C5, D1 | ⏳ pending | |

### Edits already made to working tree (uncommitted, all legitimate A3 fixes)

1. `engine/solvent_matrix.py:19` — `_SOLVENT_PROPERTIES: dict[str, dict[str, object]]` (was `float`)
2. `engine/formula_metadata.py:17-28` — added `from collections.abc import Callable`; module-level `_normalize_fallback(name: str) -> str` and `_suggest_fallback(name: str, inventory_names: set[str]) -> str`
3. `engine/formula_metadata.py:214-220` — `_normalize: Callable[[str], str]` declared before try block; fallback bound to `_normalize_fallback`
4. `engine/formula_metadata.py:242-248` — same pattern for `_suggest: Callable[[str, set[str]], str]` → `_suggest_fallback` (fixed broken indentation from rev1 partial run)
5. `engine/kb_migrate.py:300, 866` — added `# type: ignore[reportGeneralTypeIssues]` on the two `for item in IFRA_CAT4_LIMITS:` iteration sites (resolves `Never is not iterable`)
6. `engine/reference_contracts.py:13` — added `cast` to typing import
7. `engine/reference_contracts.py:575, 631` — wrapped both `ev['missing_groups']` in `cast(list[str], ...)` at the `', '.join(...)` call sites
8. `scripts/verify_formula_protocol.py:218` — added `-> dict[str, object]` return annotation to `verify_formula_protocol`
9. `scripts/build_perfume_kb.py:16` — added `from collections.abc import Mapping`
10. `scripts/build_perfume_kb.py:35` — `emit_jsonl(entry: Mapping[str, object])` (covariant; eliminates the invariance errors at call sites)
11. `scripts/build_perfume_kb.py:163, 210` — renamed local dict to `ref_entry` / `fam_entry: dict[str, object]` at the phase-4 and phase-5 emit sites (resolves `list[...] not assignable to str` and hoisting-name-obscuring warnings)

### A3 — exact fix needed for the 4 remaining errors in `verify_formula_protocol.py`

All 4 errors are in `main()` (lines 308–314 / current-file 323–330 after the +1 line shift from edit #8):

```
308:18 - error: "object" is not iterable              → for b in report.get("hard_blocks", []):
311:18 - error: "__getitem__" not defined on "object"   → report.get("warnings", [])[:10]
313:41 - error: Cannot access attribute "get" for "object" → report.get("categories", {}).get("A.8_sensomics")
314:24 - error: "__getitem__" not defined on "object"   → report['categories']['A.8_sensomics']['disclaimer']
```

**Root cause**: `report` is initialized at line 232 as a dict literal with keys `verified_at`, `categories`, `total_blocks`, `total_warns`, `all_passed`. Pyright infers `dict[str, object]`. `report.get("hard_blocks", [])` returns `object` (unknown key → returns the default merged with V), so iterating/slicing/indexing on it fails.

**Fix (smallest change, 2 edits)**:
1. Annotate the report dict explicitly: `report: dict[str, object] = {...}` at line 232.
2. Add the missing keys to the initial dict so pyright knows they exist:
   ```python
   report: dict[str, object] = {
       "verified_at": "",
       "categories": {},            # already present
       "hard_blocks": [],           # NEW
       "warnings": [],              # NEW
       "total_blocks": 0,
       "total_warns": 0,
       "all_passed": False,
   }
   ```
3. At the `report.get("categories", {}).get(...)` and `report['categories']['A.8_sensomics']['disclaimer']` sites (lines ~329–330), insert a `cast(dict[str, object], report.get("categories", {}))` once, then use the local. OR — because `categories` IS in the initial dict and `"hard_blocks"`/`"warnings"` will now be too — the `.get()` calls will naturally return `object` still because the value type is `object`. So the cast at the chained access site is required regardless.

**Cleanest path** (1 edit at the indexing sites): replace
```python
if report.get("categories", {}).get("A.8_sensomics"):
    print(f"\n{report['categories']['A.8_sensomics']['disclaimer']}")
```
with
```python
cats = cast(dict[str, object], report.get("categories", {}))
a8 = cats.get("A.8_sensomics")
if isinstance(a8, dict):
    print(f"\n{a8.get('disclaimer', '')}")
```
(Requires `from typing import cast` import — add to existing `import` block at line 13–16.)

After both edits: re-verify `basedpyright scripts/verify_formula_protocol.py` → expect **0 errors**. Then re-verify A1 + A2 still pass (annotations don't break py_compile or ruff, but confirm).

---

## DeepSeek delegation strategy (rev 3, per user directive)

**Orchestration model**: I (GLM-5.2, this session) am the **orchestrator** — I read context, make synthesis/writing decisions, and verify outputs at crystalline quality. **DeepSeek agents** (via `task` tool, model `deepseek/deepseek-v4-flash` for readers/drivers, `deepseek/deepseek-v4-pro` for the debugger) handle **mechanical, parallelizable, read-only or bounded-edit** work.

### Skills and tools I will use

| Skill/Tool | Used for |
|---|---|
| `deepseek-delegation` skill (`.opencode/skills/deepseek-delegation/`) | The parallel delegation protocol — reader/driver spawn rules |
| `parallel-reader` skill | Documenting the `.opencode/parallel/runner.py` contract for session-isolated jobs |
| `cached-deepseek-luna` skill | Local cache reuse, explicit path scopes, independent verification |
| `cost-aware-routing` + `provider-routing` skills | Pick the cheapest tier that preserves quality (Flash for mechanical; Pro for debug; GLM-5.2 for synthesis) |
| `verification-ladder` skill | Order checks from cheap (file-exists, py_compile) to full release verification; prevent redundant runs |
| Perfume KB MCP server (`perfume_kb_*` tools) | Cross-reference material properties during C1 (VP source) and C2 (hedonic) remediation |
| `pubchem_*` MCP tools | Pull experimental VP / hedonic-adjacent data for C1/C2 |
| Sequential thinking MCP (`sequential_thinking_sequentialthinking`) | Multi-step reasoning for C1 tier-selection and C2 hedonic valence ranking decisions |
| Memory MCP (`memory_*`) | Persist remediation decisions as knowledge-graph entities for next session continuity |
| env-guard plugin | Confirms `_LDLIB_LIBRARY_PATH` / `_PERFUME_PIPELINE_AUDIT_PATH` env are set before any pipeline gate run |
| gate-cache-guard plugin | Avoids re-running unchanged formulas through the pipeline (cache invalidation by SHA) |
| `inventory-guard` plugin | RULE 0 enforcement — blocks formula edits that reference depleted/non-inventory materials |

### Delegation map (which todo gets delegated, which orchestrator-only)

| Todo | Delegated to | Orchestrator (me) |
|---|---|---|
| A3 final 4-error fix | — | I write it directly (1 synthesis edit, behavior-preserving). Too small to delegate. |
| A4 (root pytest) | 1 deepseek-reader agent reads `tests/` failure traceback; 1 deepseek-driver fixes any regression I approve | I review the pass/fail delta vs. baseline and decide what ships. |
| A5 (backend pytest) | 1 deepseek-reader agent parses `backend/tests/` results | I decide what to keep/revert. |
| A6d (W7 smoke run) | 1 deepseek-driver runs `python scripts/verify_formula_protocol.py --pipeline <extant.json> --formula <extant.md>` and returns the categorized report | I judge whether the report shape matches Plan v4 spec. |
| A7 (BOM strip) | 1 deepseek-driver writes the 4 library files back as plain UTF-8 | I verify via `python -c "json.load(open(f))"` with default encoding. |
| A8 (merge truths) | 1 deepseek-reader scans `.omo/evidence/` for `merge_truths.py` and reports the CLI; 1 deepseek-driver runs it | I compare the resulting count vs. weakness-report's 1,364 and decide whether to accept. |
| A9 (consolidated commit) | — | I author the commit message + select the file manifest (synthesis decision — files must be hand-curated to exclude scratch). Driver can stage. |
| A10 (push) | — | I trigger it after A9 review. |
| B1 (Lime/Cocoa OAV) | 1 deepseek-driver applies the 2-line fix at `formula_state.py:252-257,661-666`; 1 deepseek-reader re-gates Osmanthus_Aventus_Explorer and extracts the Lime row OAV | I verify the Lime row OAV went from 0 → >1 perceptible. |
| B2 (LNDL Chamomile) | 1 deepseek-driver runs the 3-command gate sequence; 1 deepseek-reader extracts the OAV table + temporal windows from JSON | I write the 8-section perfumer analysis (synthesis — requires perfume vocabulary), present verbatim in chat, then driver appends to formula file. |
| B3 (Cassis Iris Smoke) | 1 deepseek-driver gates; 1 deepseek-reader extracts analysis | I write the perfumer analysis and IFRA Oakmoss decision (reduce to 60 µL if 0.12% flags). |
| B4 (Aventus Chypre Fruity) | 1 deepseek-reader investigates which formula file is current (Osmanthus_Aventus_Explorer vs. existing); 1 deepseek-driver applies the 3 deltas + gates | I review the chypre character preservation per RULE 3 and write the analysis. |
| C1 (VP source) | 5 parallel deepseek-reader agents split the top-50 materials → each pulls NIST/PubChem/EPI via `pubchem_get_compound_details` MCP; 1 deepseek-driver writes `vp_source` into YAML | I arbitrate tier order (NIST_exp > PubChem_exp > EPI_est > PROF_PARF) and review the audit_vp_sources.py output. |
| C2 (hedonic) | 3 parallel deepseek-reader agents each pull 17 hedonic valences from published sources (RIFM panels, Dravnieks atlas, GC-O assessments) and return structured JSON | I rank the hedonic valences, write `_HEDONIC_OVERRIDES`, and add citation back-references to `citations.jsonl`. |
| C3 (EU allergens) | 1 deepseek-reader verifies each of the 82 entries has the required fields ({INCI, CAS, threshold_leaveon_pct, threshold_rinseoff_pct, typical_occurrence}) | I decide whether partial entries get backfilled by me (synthesis from literature) or by a driver lookup. |
| C4 (biochem/neuro) | 1 deepseek-reader compiles the 5 literature pairs with evidence levels from a literature scan; 1 deepseek-driver runs `populate_receptor_data.py` over the cached CID list | I write `_PSYCHOACTIVE_EFFECTS` with evidence-level assignments (synthesis — this is a chemistry judgment call, not a mechanical edit). |
| C5 (batch testing) | 1 deepseek-driver re-runs `batch_gate_all_formulas.py --brief generic --json`; 1 deepseek-reader parses the ERROR pattern and proposes the structured-WARN fix | I decide whether the WARN downgrade preserves the surfacing intent per the risk note. |
| D1 (cost ledger) | — | I write the monthly summary synthesis. |

### Cost ceiling per wave

- Each parallel DeepSeek agent batch: ~$0.04 (Flash readers, 4-8 agents × 2-4K tokens).
- Each driver edit: ~$0.04–0.06 (Pro driver).
- Per B-todo perfumer analysis written by me (GLM-5.2 max, Tier 2): ~$0.12.
- Phase A total: ≤ $0.10. Phase B total: ≤ $0.30. Phase C total: ≤ $0.40. **Whole replan: ≤ $0.80.** Still under v5's $1.30 build cap.

---

## Phase A (rev 3) — Lock-down & Verification Gates

- [x] **A0 — Deepluna guard** ✅
- [x] **A1 — py_compile 16 modules** ✅
- [x] **A2 — ruff regression** ✅
- [ ] **A3 — basedpyright gate** 🟡 4/16 errors remain in `verify_formula_protocol.py`. Fix per the exact recipe above (1 annotation + 1 cast block, both at lines 232/329-330). Then re-verify all 16 modules → 0 errors. (I write this directly; too small to delegate.)
- [ ] **A4 — Pytest baseline (repo root)** — delegate: 1 reader + conditional driver; orchestrator decides what ships.
- [ ] **A5 — Backend pytest baseline** — delegate: 1 reader.
- [ ] **A6d — W7 verify_formula_protocol smoke run** — delegate: 1 driver runs the CLI; orchestrator verifies report shape.
- [ ] **A7 — Re-encode library files as plain UTF-8 (no BOM)** — delegate: 1 driver. Orchestrator verifies via default-encoding json.load.
- [ ] **A8 — Merge truths diff** — delegate: 1 reader scans for merge script + 1 driver runs it. Information-only.
- [ ] **A9 — Consolidated commit** — orchestrator authors commit message + file manifest (exclude scratch: `out_err.txt`, `_*.py` root scratch, `.omo/run-continuation/`); driver stages.
- [ ] **A10 — Push** — orchestrator triggers.

**Wave A acceptance**: A3 → 0 basedpyright errors. A4/A5 reach recorded baseline. A7 BOM stripped. A9 single coherent commit ahead of `dba99ec`. A10 pushed.

---

## Phase B (rev 3) — Close the four leftover patch plans

For each, the delegation pattern is: driver runs the gate sequence → reader extracts the OAV table + temporal windows from the JSON → **orchestrator writes the 8-section perfumer analysis with perfume vocabulary** (RULE 2 of copilot-instructions.md), presents verbatim in chat first, then driver appends `## Pipeline Analysis` to the formula file. RULE 0 (read `inventory.txt`) enforced by `inventory-guard` plugin before each formula edit.

- [ ] **B1 — Lime & Cocoa OAV bug** (`engine/pipeline/formula_state.py:252-257, 661-666`): fall through to monomolecular Raoult OAV when natural is unmodeled. Re-gate Osmanthus_Aventus_Explorer; verify Lime row OAV > 1.
- [ ] **B2 — LNDL Chamomile complete** (tasks 4, 5, 8, 9): gate `La_Nuit_de_Bleu_Chamomile_30mL_EDP.md` with `--brief aromatic_fougere`. Orchestrator writes 8-section perfumer analysis.
- [ ] **B3 — Cassis Iris Smoke** (tasks 4–6 + F1–F4): gate `Cassis_Iris_Smoke_30mL_EdP.md` (6000 µL, brief generic). IFRA Oakmoss: if 72 µL/10% = 0.12% flags, drop to 60 µL.
- [ ] **B4 — Aventus Chypre Fruity**: investigate which formula file is current; apply 3 deltas (Hydroxycitronellal → Mayol + Farnesol; Ambrox Super 30% dose to 3-5% active; Damascone Beta ≤ 12 µL); gate; orchestrator reviews chypre character preservation per RULE 3.

---

## Phase C (rev 3) — Remediate the 5 weaknesses

Reference: `.omo/evidence/weakness_report.md`. NOTE: weaknesses #3 (EU allergens) and phototoxic data may already be substantially closed by the v5 build — verify before remediation.

- [ ] **C1 — VP Source vacuum** (priority 1, blocks A.7 production-release gate). 5 parallel readers split top-50 materials, pull NIST/PubChem/EPI via `pubchem_get_compound_details` MCP. Driver writes `vp_source` into `data/materials/*.yaml`. Orchestrator arbitrates tier order: NIST_exp > PubChem_exp > EPI_est > PROF_PARF. Target: top-50 have non-`UNKNOWN` `vp_source`.
- [ ] **C2 — Hedonic Data Desert** (priority 2). 3 parallel readers each pull 17 hedonic valences from RIFM/Dravnieks/GC-O sources as structured JSON. Orchestrator ranks valences, writes `_HEDONIC_OVERRIDES` in `engine/hedonic_model.py`, adds citations to `citations.jsonl`. Target: `len(_HEDONIC_OVERRIDES) >= 50`.
- [ ] **C3 — EU 2023/1545 82-allergen completeness verification** (priority 3). 1 reader verifies each of 82 entries has {INCI, CAS, threshold_leaveon_pct, threshold_rinseoff_pct, typical_occurrence}. Orchestrator decides: partial entries backfilled by me (from literature) or by driver lookup. Preserve v5 user-locked behavior: WARN not FAIL.
- [ ] **C4 — Biochem/Neuro near-zero** (priority 4). 1 reader compiles the 5 literature pairs (linalool→GABA-A [Buchbauer 1993], limonene→5-HT/DA, eugenol→TRPV1, menthol→TRPM8, β-caryophyllene→CB2 [Gertsch 2008]) with evidence levels. 1 driver runs `populate_receptor_data.py` over cached CID list. **Orchestrator writes `_PSYCHOACTIVE_EFFECTS` in `engine/pipeline/neuroscience.py`** (chemistry judgment call, not mechanical). Target: ≥50 materials with ≥1 psychoactive mapping.
- [ ] **C5 — Batch Testing gap** (priority 3). 1 driver re-runs `batch_gate_all_formulas.py --brief generic --json`; 1 reader parses the ERROR pattern. Orchestrator decides whether the WARN downgrade preserves the surfacing intent per the risk note (do not silence the gap). Target: ≥15 formulas `PASS` or `WARN` (not ERROR).

---

## Phase D (rev 3) — Recurring burn / cost gate

- [ ] **D1 — Monthly cost ledger** — orchestrator writes monthly summary synthesis in `.omo/start-work/ledger.jsonl`. Stop-the-line if a single wave exceeds 1.5× the per-wave cap without user approval.

---

## Acceptance criteria (overall, unchanged from rev 2)

1. **All Phase A gates A0–A10 pass.** A3 reaches 0 basedpyright errors. A9 single consolidated commit ahead of `dba99ec`.
2. **All Phase B patch plans B1–B4 closed.** Each formula file has appended `## Pipeline Analysis`; analysis presented verbatim in chat by orchestrator.
3. **All Phase C remediation C1–C5 closed.** 50-MVP thresholds met; `len(eu_2023_1545_allergens) == 82` with required fields; batch test ≥15 PASS/WARN.
4. **No rules broken**: RULE 0 (inventory-guard plugin enforces), RULE 1 (ppm/ODT/OAV throughout), RULE 2 (no new pipeline scripts — reuses existing), RULE 3 (each formula still smells of its name — orchestrator reviews post-gate), RULE 4 (composite OAV preserved).
5. **No v5 locked revision violated**: A.2/A.3/A.6 stay WARN (not hard block), Oakmoss CoA gate denied, GLM-5.2 max flex as Tier 2 sign-off.
6. **DeepSeek delegation**: every delegated sub-result is verified by the orchestrator (me, GLM-5.2) before being accepted into the baseline. No agent output is merged unreviewed.

## Out of scope (deferred to separate plans, unchanged)

- ATELIER_PIPELINE_PLAN.md phases 1–5 (engine/orchestration/ generative pipeline)
- New fragrance family archetypes (Edwards 14 backfill)
- Frontend / backend API redesign for the orchestrator (Track F of rest-of-implementations)
- IEC human-in-loop mode (ATELIER Stage 6)
- Track F physics overhaul (UNIFAC stub replacement, finite-film evaporation, maturation kinetics refinement, material-pair-specific psychophysical suppression)
- Phase 1A backend Models/CRUD beyond the migration that's already built

---

## Risk notes (rev 3)

- A3 is now the lowest-risk gate: only 4 errors remain, the fix is 1 annotation + 1 cast block.
- DeepSeek agent delegation failure mode: cancelled agents (the v4-issue the `glm-5.2-parallel-delegation` plan was supposed to fix). If `oh-my-openagent.json` config is live (it is — verified `maxToolCalls: 120`, `defaultConcurrency: 15`), expect ~0% cancellation. If an agent IS cancelled, the orchestrator **falls back to inline execution** per `agent-deepseek-driver` / `agent-deepseek-reader` skill spec (no retries, no wasted spend).
- The 4 verify_formula_protocol errors are behavior-preserving type annotations — there is zero risk of changing the verification protocol's actual logic.
- Phase B2/B3 depend on Phase A9 (commit) so gated formulas sit on a clean baseline.
- Orchestrator (me) keeps synthesis authority for all perfumer analysis text (RULE 2 perfume vocabulary) and all chemistry judgment calls (hedonic ranking, evidence-level assignment, VP tier arbitration). DeepSeek does mechanical work; I do crystalline writing.

---

## Cost estimate (rev 3)

- Phase A remaining (A3 + A4–A10): ≤ $0.10 (mostly Flash readers, 1 Pro driver).
- Phase B (B1–B4): ≤ $0.30 (driver gates + orchestrator Tier-2 perfumer analyses).
- Phase C (C1–C5): ≤ $0.40 (5-reader parallel batches + orchestrator synthesis).
- **Whole replan: ≤ $0.80.** Under v5's $1.30 build cap. Recurring burn unchanged (~$24/month).

**Ready for `/start-work`.**