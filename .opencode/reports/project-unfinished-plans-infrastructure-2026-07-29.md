# Perfume-Chem — Unfinished Plans & Infrastructure Audit

**Date:** 2026-07-29  
**Branch:** `codex/add-inventory-materials` (diverge from `master`)  
**Git state:** 93 modified files (8,203 +, 2,280 −), ~160 untracked files, 1 stash  
**Last commit:** `2e46e4c` — "chore: remove redundant opencode-perfume launch scripts"

---

## 1. Plan Inventory — 27 Approved, 0 Executed

There are **27 approved but unimplemented plans** in `~/.plannotator/plans/`. None have been fully executed.

### 1.1 Reconstruction System (highest priority, largest scope)
| Plan | Scope |
|------|-------|
| `integration-plan-full-reconstr-approved.md` | 6-phase: foundation modules → reconstruction modules → accord/chassis → pipeline integration → live batch → compliance |
| `continuation-plan-remaining-ph-approved.md` | 6 modules + 6 tests for unfinished reconstruction pieces |
| `audit-document-reconstruction-approved.md` | 12-section comprehensive audit of all 40 reconstruction files |

**Status:** 22 new engine modules created (untracked), ~17 test files created (untracked), 7 CLI modes are stubs, build ledger NOT STARTED, 15/22 dataclasses missing `from_dict()`.

### 1.2 v5 Pipeline Completion
| Plan | Scope |
|------|-------|
| `plan-v5-executable-build-remai-approved.md` | Waves 4-8: metadata parser, preflight guard, citations, verify_formula_protocol |
| `plan-v5-r-replan-rev-3-consoli-approved.md` | Consolidate A3-A10 gate verifications, close 4 leftover patch plans |
| `plan-remaining-waves-5d-8-approved.md` | Extend 6 scripts with metadata parsing, add 3 new gates |
| `plan-final-completion-gate-reg-approved.md` | Register 2 new gates + force-test pipeline |

**Status:** A3 (gate fixes) is 96% done (12/16 bugs fixed, 4 remain). Most waves are NOT STARTED.

### 1.3 Hardening & Quality
| Plan | Scope |
|------|-------|
| `hardening-phase-fix-connect-an-approved.md` | 9-pass hardening: 6 blocking bugs, 30+ dataclass serializers, event replay, inventory depletion, dead code removal, 60+ tests |
| `next-steps-plan-post-hardening-approved.md` | Wave 1-6: 80 tests, 3 formula gates, evidence-to-authority bridge, 7 CLI stubs, documentation |

**Status:** 6 blocking bugs documented, 4 of 6 still unfixed. `from_dict()` deserializers missing for 15 dataclasses.

### 1.4 Naturals & Chemistry Data
| Plan | Scope |
|------|-------|
| `plan-methodologically-rigorous-approved.md` | 54 neuroscience references + 15 natural constituent expansions |
| `plan-next-implementation-natur-approved.md` | Expand 15 naturals, solvent matrix gate, VP source audit |
| `plan-optimal-quality-models-vp-approved.md` | VP source hierarchy audit (NIST > EPI > PubChem), 5 remaining naturals |

**Status:** 14 of 15 naturals expanded, remaining naturals (Tuberose, Osmanthus VG, Cocoa) not started.

### 1.5 Codex Desktop Fixes (today)
| Plan | Scope |
|------|-------|
| `fix-codex-desktop-litellm-glm-approved.md` | Root cause analysis of GLM 5.2 in account area |
| `fix-codex-desktop-chatgpt-fail-approved.md` | State recovery from broken provider |
| `fix-providerdeepinfrawire-api-approved.md` | wire_api validation fix |

**Status:** COMPLETED — all 3 executed in this session.

### 1.6 Delegation & Workflow
| Plan | Scope |
|------|-------|
| `plan-register-deepseek-only-de-approved.md` | Register 3 DeepSeek subagents |
| `plan-next-session-delegate-exp-approved.md` | 15 delegated expansion tasks |
| `wire-cheapluna-mcp-produce-cod-approved.md` | CheapLuna MCP wiring + report generation |

---

## 2. Infrastructure Gaps — BREAKING (must fix before release)

### B1. 25 Duplicate ODT_DATA Entries
**File:** `engine/odor_thresholds.py`

`ODT_DATA` and `ODT_VERIFICATION` are supposed to be separate dicts (per AGENTS.md), but they're merged into ONE dict. 25 materials have their numeric ODT values partially overwritten by later audit-metadata-only entries. Affected: iso e super, hedione, bergamot variants, tobacco absolute, and 20 more.

### B2. 12 Inventory Materials Missing ODT_DATA
Materials in `inventory.txt` with **no ODT entry**:

| Material | Added |
|----------|-------|
| Cade Oil Rectified | 2026-07-05 |
| Cassia EO | 2026-06-15 |
| Peppermint EO | 2026-06-15 |
| Eucalyptus EO | 2026-06-15 |
| Blue Chamomile EO | 2026-06-22 |
| Tagetes EO | 2026-06-22 |
| Cocoa CO₂ Extract | 2026-06-22 |
| Peru Balsam Resinoid | 2026-06-22 |
| Opoponax Resinoid | 2026-06-22 |
| Tonka Bean Absolute | 2026-06-22 |
| Benzoin Sumatra Resinoid | existing |
| Tuberalia base | existing |

Pipeline will silently assign ODT=1.0 or fail lookup for these.

### B3/B4. _PROFILES ↔ ODT_DATA Asymmetry
- **10 materials** in `_PROFILES` but not in `ODT_DATA`
- **77 ODT_DATA keys** not in `_PROFILES`
- **Ambrofix Crystals** (solid, inventory line 171) missing from BOTH

### B5. 6 Documented Critical Bugs (unfixed)
From `docs/reconstruction_implementation_audit.md`:
1. Ethanol classified as carrier (dead code)
2. UNKNOWN_IDENTITY branch is dead code
3. `create_target_from_rows()` silently drops 6 fields
4. Correction-of-correction events silently lost
5. Anti-compression 12 criteria MISMATCHED with spec
6. Division-by-zero in `rank_prior` with empty materials

### B6. 7 Documented Pipeline Bugs (unfixed)
From AGENTS.md "Common Pipeline Bugs":
1. Pyramid shows T:0% H:100% B:0% — `.lower()` key mismatch at gates.py:720
2. Pyramid ignores dilutions — calling `raw_percentages()` not `active_percentages()`
3. Material has 100M+ OAV — duplicate ODT entries
4. `--brief` has no effect — reads family_archetype raw, no infer_archetype()
5. Stale note/VPs in profiles
6. Section headers parsed as materials — flat format required
7. Pipeline parser bug — row parser triggers on any number+uL+%

---

## 3. Infrastructure Gaps — WARNING

### W1. 7 CLI Modes Are NOT_IMPLEMENTED
`scripts/reconstruct.py` has 7 stub modes returning "NOT_IMPLEMENTED":
- LIVE_BATCH, BATCH_RESCUE, SENSORY_EXPERIMENT, ANALYTICAL_INTERPRETATION, COMPLIANCE_BUILD, RELEASE_REVIEW (partial), INVENTORY_MAPPING

### W2. 3 Backend AI Services Not Implemented
`backend/app/services/ai/base.py`: `analyze()`, `suggest_modifications()`, `suggest_pairings()` all raise `NotImplementedError`.

### W3. UNIFAC Stubbed
`engine/thermo/activity.py` — `gamma()` accepts `smiles_table` but silently discards it. Only Hansen-distance heuristic operates, calibrated to single limonene-in-EtOH checkpoint.

### W4. TRANSFER Event Dead Code
`engine/bottle/events.py` — `TRANSFER` event is a no-op, tagged with TODO. Multi-batch transfer requires atomic source/destination access.

### W5. Reconstruction Module Completion
| Module | Rating |
|--------|--------|
| Evidence Ledger | 70% |
| Target Ledger | 60% |
| Inventory Ledger | 55% |
| Build Ledger | **NOT STARTED** |
| Bottle Ledger | 75% |
| Analysis Ledger | 55% |
| Sensory Ledger | 60% |

### W6. Test Coverage — ~140 Untested Engine Modules
Of ~179 engine modules, approximately 140 have no dedicated test. Critical untested: `natural_absolute_decomposition`, `ingredient_intelligence`, `name_utils`, `thermo/activity`, `thermo/antoine`, `ifra_safety`, `solvent_matrix`, `pipeline/formula_state`.

### W7. material_properties.json Coverage
- Hedonic: 161/210 (77%)
- IFRA Cat4 limit: 87/210 (41%)
- Hill EC50: 25/210 (12%)

### W8. Inconsistent VP Data Across 3 Sources
`Methyl Ionone Pure` VP: 0.4 Pa (AGENTS.md), 1.0 Pa (diffusion_model.py), ? Pa (material_properties.json). Three data paths out of sync.

---

## 4. Knowledge & Science Gaps

### 4.1 Scientific Contract Open Questions (5)
From `docs/SCIENCE_PLAN.md`:
- Mixture-shift β coefficient uncalibrated
- Stevens vs Weber-Fechner unresolved for perfumery
- Retronasal weighting unmodeled
- Receptor coverage: 8 of 396 human OR genes
- Adaptation τ: rat values, human may differ 2-3×

### 4.2 Model Inventory Gaps
- Longevity in hours: `UNKNOWN` (withheld as null)
- Sillage category: `UNKNOWN` (withheld as null)
- Receptor activation: `UNKNOWN` (withheld as null)

### 4.3 OAV Claims Are Heuristic
Pipeline OAV is "heuristic, matrix-omitted, and not a sensory-equivalence claim" (AGENTS.md:636).

---

## 5. Working Tree State (Git)

| Metric | Value |
|--------|-------|
| Branch | `codex/add-inventory-materials` |
| Modified files (staged) | 93 |
| Untracked new files | ~160 |
| New engine modules (untracked) | ~22 |
| New test files (untracked) | ~18 |
| New formulas (untracked) | 6 |
| New docs (untracked) | 10 |
| Stashed changes | 1 |

The working tree contains the entire reconstruction system (22 engine modules, 17 tests, 10 docs) that has **never been committed**. Largest diffs: `science_audit.json` (+1813 lines), `ifra_safety.py` (+669 lines), `pipeline/gates.py` (+480 lines).

---

## 6. Recommended Action Order (for Sol Review)

### Immediate (block release)
1. **Fix ODT_DATA duplicates (B1)** — split into `ODT_DATA` + `ODT_VERIFICATION` dicts
2. **Add ODT entries for 12 missing materials (B2)** — June 2026 additions need thresholds
3. **Fix 6 critical reconstruction bugs (B5)** — documented in audit

### High Priority (this week)
4. **Implement Build Ledger** — last zero-coverage reconstruction module
5. **Fix 7 documented pipeline bugs (B6)** — with known fix locations
6. **Implement `from_dict()` for 15 dataclasses** — blocks serialization round-trips
7. **Re-sync _PROFILES ↔ ODT_DATA (B3/B4)** — 87 entries cross-missing

### Medium Priority
8. **Commit reconstruction system** — 22 modules + 17 tests are untracked
9. **Implement 7 CLI stub modes** — `reconstruct.py` NOT_IMPLEMENTED stubs
10. **Add Ambrofix Crystals data (W2)** — missing from both data stores
11. **Implement 3 backend AI services** — `analyze`, `suggest_modifications`, `suggest_pairings`

### Nice to Have
12. **UNIFAC implementation** — replace Hansen heuristic with proper group-contribution
13. **Test coverage** — 140 untested engine modules
14. **OR receptor coverage** — expand from 8 genes to 30+ for family-level receptor mapping

---

## 7. File Index

| File | Role |
|------|------|
| `C:\Users\ASUS\.plannotator\plans\` | 35 plan files (27 approved, 4 denied, 4 annotations) |
| `D:\chatbots\perfume-chem\.omo\plans\` | ~15 plan markdown files with TODO checklists |
| `D:\chatbots\perfume-chem\engine\reconstruction\` | 8 modules (new, untracked) |
| `D:\chatbots\perfume-chem\engine\bottle\` | 5 modules (new, untracked) with TRANSFER TODO |
| `D:\chatbots\perfume-chem\engine\evidence\` | 3 modules (new, untracked) |
| `D:\chatbots\perfume-chem\engine\target\` | 3 modules (new, untracked) |
| `D:\chatbots\perfume-chem\engine\sensory\` | 2 modules (new, untracked) |
| `D:\chatbots\perfume-chem\engine\identity\` | Material identity model (new, untracked) |
| `D:\chatbots\perfume-chem\engine\units\` | Concentration engine (new, untracked) |
| `D:\chatbots\perfume-chem\engine\versioning\` | Formula versioning (new, untracked) |
| `D:\chatbots\perfume-chem\engine\inventory\` | Stock model (new, untracked) |
| `D:\chatbots\perfume-chem\scripts\reconstruct.py` | CLI with 7 NOT_IMPLEMENTED stubs |
| `D:\chatbots\perfume-chem\docs\reconstruction_implementation_audit.md` | 6 critical bugs documented |
| `D:\chatbots\perfume-chem\docs\SOL_DEXTERITY_REPORT.md` | Architecture gaps assessment |
| `D:\chatbots\perfume-chem\engine\odor_thresholds.py` | 25 duplicate entries |
| `D:\chatbots\perfume-chem\engine\ingredient_intelligence.py` | 77 entries without ODT; 10 without _PROFILES |
| `D:\chatbots\perfume-chem\backend\app\services\ai\base.py` | 3 NotImplementedError services |
| `D:\chatbots\perfume-chem\engine\thermo\activity.py` | UNIFAC stubbed |
| `D:\chatbots\perfume-chem\engine\bottle\events.py` | TRANSFER no-op |

---

*Generated by manual exploration (4 parallel agents) in this session. CheapLuna MCP was configured but not connected — requires OpenCode restart to pick up `opencode.json` MCP changes.*
