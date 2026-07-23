# Plan v5 — Executable Final (Revisions Locked by User 2026-07-21)

**Status**: APPROVED FOR EXECUTION via `/start-work`
**Author**: Prometheus (high variant) running as GLM-5.2 max
**Date**: 2026-07-21

---

## User-Locked Revisions (binding on orchestrator)

1. **Tier 0A (Light chat)**: `deepinfra/deepseek-v4-flash` — "what is X" + brute-force pipeline testing
2. **Tier 0B (Brainstorm)**: `deepinfra/deepseek-v4-pro` — concept chat (Flash is "shit at perfume")
3. **Tier 1 (Orchestrator)**: `deepinfra/deepseek-v4-flash` — pure delegation of GLM-5.2 max's commands
4. **Tier 2 (Head perfumer/scientist/engineer/final gate)**: `deepinfra/zai-org/GLM-5.2` max, flex tier (0.8×), 1-2× per session
5. **Tier 3 (Oracle)**: `deepseek/deepseek-v4-pro` DeepSeek-direct priority — Tier 2 aborts 2× fallback
6. **Allergens / phototoxicity / skin sensitization = WARNs**, NOT hard blocks. Auto-recommend Perfumer's World substitutes + emit two alternative formula versions (inventory + PW purchase).
7. **Oakmoss CoA gate: DENIED** — WARN only. IFRA exceed → recommend Evernyl substitution.
8. **GLM-5.2 self-certification of Plans v3/v4 accepted.**
9. **Plan v4 Phase 1 Perfumer's World JSONL library: MANDATORY.**

---

## TODOs

### Wave 1 — Config lockdown (Tier 0A Flash, 15 min)

1. [✓ MANUAL] Fix JSON syntax error in `opencode.json` — the `_note_overrides` key I added earlier inside `permission` object (lines 35-37) is invalid JSON schema and prevents OpenCode from booting. **User must delete this line manually before OpenCode can start.** Once deleted, this checkbox is satisfied without worker effort.
2. [ ] Flip `deepluna_read.enabled: true → false` in `opencode.json` (do NOT touch `~/.codex/config.toml` — Codex keeps DeepLuna)
3. [ ] Flip `deepluna_fast_read.enabled: true → false` in `opencode.json`
4. [ ] Add `DEEPINFRA_SERVICE_TIER` env passthrough in `.opencode/plugins/env-guard.js` — default "standard", overridable per process
5. [ ] Append `.opencode/parallel/jobs/`, `.opencode/cache/`, `.opencode/library/` to `.gitignore`
6. [ ] Run provider verification curls (DeepInfra, DeepSeek, OpenCode Go) — all three must return HTTP 200
7. [ ] Verify `~/.codex/config.toml` file is untouched (Codex keeps DeepLuna active)

### Wave 2 — Parallel reader/brain framework (Tier 0A Flash, 45 min)

8. [ ] Create `.opencode/parallel/runner.py` — stdlib only (os, sys, json, hashlib, time, pathlib, argparse, subprocess, msvcrt, urllib.request, urllib.error)
9. [ ] Implement submit/status/collect/list/cleanup CLI subcommands
10. [ ] Session isolation via `OPENCODE_SESSION_ID` env var — runner refuses to operate if missing
11. [ ] Atomic writes via `.tmp` → `os.replace()`
12. [ ] Cross-process file lock via `msvcrt.locking` (Windows) / `fcntl.flock` (POSIX) on `job.lock`
13. [ ] Stale lock reclaim after 30 min (env `STALE_LOCK_MINUTES=30`) if holding PID no longer alive
14. [ ] Status enum: `pending`, `running`, `complete`, `failed`, `stale_reclaimed`
15. [ ] `collect` refuses output unless `status.json` says `complete | stale_reclaimed`
16. [ ] Create `.opencode/parallel/README.md` (≤50 lines, contract + usage)
17. [ ] Create empty `.opencode/parallel/__init__.py`
18. [ ] Verify `python -m py_compile .opencode/parallel/runner.py` returns exit code 0
19. [ ] Smoke test: `python -m runner submit --kind read --path README.md --reader flash` returns a job_id, then `status <job_id>` then `collect <job_id>` roundtrips
20. [ ] Write `.opencode/plugins/gate-cache-guard.js` — wraps `formula_release_gate.py` bash invocations to check/invalidate local gate cache at `.opencode/cache/gate_results/<sha256>.json`
21. [ ] Write `.opencode/plugins/parallel-runner-guard.js` — `OPENCODE_SESSION_ID` uniqueness across running OpenCode windows (checks `tasklist /v | findstr opencode` on Windows)
22. [ ] Write `.opencode/plugins/provider-tier.js` — auto-sets `DEEPINFRA_SERVICE_TIER` env based on task shape (chat=standard, async gate=flex, brain=flex, oracle=priority)

### Wave 3 — Skills (Tier 0A Flash, 20 min)

23. [ ] Write `.agents/skills/provider-routing/SKILL.md` — tier decision matrix, loaded at session start
24. [ ] Write `.opencode/skills/perfume-library-query/SKILL.md` — JSONL retrieval contract
25. [ ] Write `.opencode/skills/parallel-reader/SKILL.md` — runner.py contract
26. [ ] Extend `.opencode/skills/formula-gate/SKILL.md` with metadata-block enforcement + preflight guard docs

### Wave 4 — Perfume library Phase 1 (Tier 0A Flash + Tier 2 GLM max flex review, 25 min)

27. [ ] Write `scripts/build_perfume_kb.py` (stdlib only)
28. [ ] Parse `data/materials/_sources/perfumersworld_stock.parsed.json` → emit `pw_sku_*` entries
29. [ ] Parse `inventory.txt` → emit `local_inv_*` entries + set `in_local_inventory=true` on matching PW entries
30. [ ] Parse `engine/odor_thresholds.py` ODT_DATA → emit `odt_*` entries
31. [ ] Parse `engine/reference_contracts.py` REFERENCE_CONTRACTS → emit `ref_*` entries
32. [ ] Parse `engine/families/registry.py` ARCHETYPES → emit `fam_*` entries
33. [ ] Output all to `.opencode/library/perfume_kb.jsonl` (one JSON per line)
34. [ ] Smoke test: `grep -F '"name": "hedione"' .opencode/library/perfume_kb.jsonl` returns at least one matching line
35. [ ] **Tier 2 gate 1 of 2**: spawn GLM-5.2 max flex review of library for chemistry/physics validity. Acceptance: GLM-5.2 max returns `confirmed` on character-impact weighting for vetiver (khusimone, α/β-vetivone), osmanthus (β-ionone), cedarwood (α-cedrene), oakmoss (methyl atratate).

### Wave 5 — Pipeline preflight + format unification (Tier 1 Flash + Tier 2 GLM max, 60-90 min)

36. [ ] Add `parse_formula_metadata()` helper to `engine/formula_state.py` or new `engine/formula_metadata.py` (~50 LOC)
37. [ ] Add `pipeline_preflight_guard()` to `scripts/formula_release_gate.py` (~80 LOC)
38. [ ] Add `pipeline_preflight_guard()` to `scripts/pipeline_audit.py` (~80 LOC)
39. [ ] Preflight Block 1: metadata required unless explicit `Reference claim: none`
40. [ ] Preflight Block 2: inventory stock contract (HARD block)
41. [ ] Preflight Block 3: quantitative authority if claimed (HARD block)
42. [ ] Preflight Block 4: chemical family compatibility (F11 — WARN with substitute suggestions)
43. [ ] Preflight Block 5: Thai retail bracket cost (WARN if >5000 THB)
44. [ ] Preflight Block 6: EU 2023/1545 82-allergen WARN (NOT hard block per user)
45. [ ] Add `_CHEMICAL_FAMILY_MAP` to `engine/ingredient_intelligence.py` (~30 entries covering citrus, floral, woody, spice, musk, leather, balsam, chypre, fougère)
46. [ ] Extend `scripts/evaluate_formula.py` with metadata-block parsing (refuse unless metadata present or `Reference claim: none`)
47. [ ] Extend `scripts/oav_headspace_analyze.py` — emit smaller JSON containing only OAV table + note distribution; reuse `format_pipeline_analysis.py` formatters
48. [ ] Extend `scripts/formula_simulator.py` — emit 5-window OAV (0s→5min→30min→2hr→4hr) only
49. [ ] Extend `scripts/formula_diagnosis.py` — emit deviation report via `build_reference_deviation()` if any named reference detected in formula header
50. [ ] Extend `scripts/formula_recommender.py` — pre-formulation only, must NOT touch main pipeline
51. [ ] Extend `scripts/opus_v_workbook_pipeline.py` with metadata-block requirement
52. [ ] Write `perfume_kb` MCP (stdlib only) exposing `query_material`, `query_family`, `query_reference_contract`, `query_sku`
53. [ ] **Tier 2 gate 2 of 2**: spawn GLM-5.2 max flex for final chemistry/thermo verification per Plan v4 Part K. Acceptance: reviewer returns `confirmed` on OAV table, receptor saturation checks, composite OAV for naturals.

### Wave 6 — Literature citations database (Tier 1 Flash, 15 min)

54. [ ] Write `.opencode/library/citations.jsonl` from Plan v4 Part L (40 entries — EU 2023/1545, SCCS/1459/11, IFRA STD 089, Emter 2024 bjae015, Ahmed 2018 PNAS, Sato-Akuhara 2023, Woo 2017 Sci Rep, Belhassen 2014, Adams 2014, Pandey 2024, Setzer 2026, Gonçalves 2024, Joulain 2009, Bouges 2018, Chittiboyina 2020, Hofmann TUM sensomics, Grosch 1994, Dunkel 2014 Angew Chem)
55. [ ] Write `.opencode/library/eu_2023_1545_allergens.json` (82 entries with INCI + CAS + threshold 0.001% leave-on / 0.01% rinse-off)
56. [ ] Write `.opencode/library/phototoxic_oils.json` (entries: Bergamot FCF Sicilian, Bergamot FCF, Bergamot EO, Lime EO expressed, Lemon EO cold pressed, Bitter Orange EO expressed, Grapefruit FCF, Grapefruit EO, Cumin EO, Angelica Root EO, Rue EO, Petitgrain Mandarin, Tangerine EO cold pressed, Parsley Leaf EO — each with `typical_bergaptene_ppm` and `ifra_max_leaveon_pct`)

### Wave 7 — Verification protocol (Tier 1 + Tier 2 GLM max, 90 min)

57. [ ] Write `scripts/verify_formula_protocol.py` (NEW) reading pipeline JSON + formula markdown
58. [ ] Implement A.1 OAV physics check (γ-not-1.0, VP source authoritative) — HARD block
59. [ ] Implement A.2 EU 2023/1545 allergen check — WARN with PW substitute suggestions (NOT hard block per user)
60. [ ] Implement A.3 Phototoxicity (bergaptene ≤15 ppm leave-on, regular bergamot cap 0.4%) — WARN with FCF substitution suggestion
61. [ ] Implement A.4 Receptor saturation (OR5AN1 macrolactones, OR5A2 polycyclic musks, OR5A1 β-ionone, OR10J5 cedarwood) — WARN
62. [ ] Implement A.5 Composite OAV for naturals — WARN if natural missing from decomposition database or sum <30%
63. [ ] Implement A.6 Skin degradation kinetics for oakmoss (atranorin → atranol, chloroatranol) — WARN only per user, NO CoA requirement, BUT if dose >IFRA limit recommend Evernyl substitute
64. [ ] Implement A.7 VP source hierarchy: NIST / EPI / PubChem_exp required for production-release (HARD block for release claim, WARN for draft)
65. [ ] Implement A.8 Sensomics disclaimer: always append disclaimer text to released formula markdown
66. [ ] Implement A.9 ΔHvap per-molecule if NIST available — informational
67. [ ] Implement A.10 Note tier classification via VP thresholds (>2Pa top, 0.1-2Pa heart, <0.1Pa base) — informational
68. [ ] Build `recommend_substitutes(material_name, violation_type, perfumers_world_json, inventory)` — looks up material in perfume_kb.jsonl, finds same chemical class PW substitutes, prefers inventory if available, emits two alternative formula versions (v_inventory.md + v_pw_purchase.md)
69. [ ] Test on `formulas/Osmanthus_Explorer_30mL_EdP.md` — expect A.2 WARN for any bergamot allergens, A.6 WARN for any oakmoss (likely none present, but smoke path)
70. [ ] Test on `formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md` — expect all gates pass with possibly A.4 WARN on ionone if any present
71. [ ] **Tier 2 GLM-5.2 max flex review**: confirm script matches protocol. Acceptance: reviewer returns `confirmed` on every verification category behavior matching the disposition table.

### Wave 8 — Pipeline integration (Tier 1 orchestrator, 60 min)

72. [ ] Add `verify_formula_protocol` as new pipeline gate in `engine/pipeline/gates.py` — status PASS/WARN (never FAIL for A.2/A.3/A.6 per user)
73. [ ] Add `vp_source` field to `data/materials/<LETTER>.yaml` schema — audit existing 210 materials for Tier 1-2 NIST/EPI/PubChem_exp sources first, flag the rest for resolution
74. [ ] Add `_CHARACTER_IMPACT_BONUS` to `engine/pipeline/natural_absolute_decomposition.py`:
   - Vetiver: α-vetivone 5×, β-vetivone 5×, khusimone 20× (per Belhassen 2014 + Adams 2014 + Pandey 2024)
   - Osmanthus: β-ionone 5× (per Hong 2023 + Guo 2024)
   - Cedarwood Virginia: α-cedrene 5×, cis-thujopsene 3× (per Setzer 2026 + Woo 2017 OR10J5)
   - Oakmoss: methyl atratate 3×, methyl-β-orcinol-carboxylate 3× (per Joulain 2009 + Bouges 2018)
75. [ ] Audit `_ABSOLUTE_CONSTITUENTS` in `natural_absolute_decomposition.py` — flag naturals with constituent sum <30% as incomplete (need gap-fill)
76. [ ] Extend `safety_ifra_allergen` gate to 82-allergen list (was 26) — threshold downgrade FAIL → WARN per user
77. [ ] Add new gate `safety_phototoxic_furanocoumarin` (WARN only) — `bergaptene_ppm ≤ 15` check
78. [ ] Add new gate `safety_receptor_saturation` (WARN only) — receptor dosing caps from Plan v4 Part E
79. [ ] **Tier 2 GLM-5.2 max flex final verification**: run on `Osmanthus_Explorer_30mL_EdP.md` — confirm all gates pass (with WARNs where expected). Acceptance: GLM-5.2 max sign-off line appended to formula markdown:
   ```
   **Verification gate passed by GLM-5.2 max:** 2026-07-21 HH:MMUTC
   Categories checked: A.1 ✓ A.2 ✓ A.3 ✓ A.4 ✓ A.5 ✓ A.6 ✓ A.7 ✓ A.8 ✓ A.9 ✓ A.10 ✓
   ```

## Final Verification Wave

F1. [ ] Full pipeline run on `Osmanthus_Explorer_30mL_EdP.md` succeeds with all gates in valid state
F2. [ ] Reference Deviation Report renders in `format_pipeline_analysis.py` output (verifies v3 Part E.3 still works)
F3. [ ] `scripts/verify_formula_protocol.py` produces WARN substitutions when violations present
F4. [ ] `scripts/build_perfume_kb.py` regenerates `perfume_kb.jsonl` idempotently
F5. [ ] `.opencode/parallel/runner.py` roundtrips a job across two simulated sessions
F6. [ ] All 8 plugin hooks (env-guard, inventory-guard, gate-cache-guard, parallel-runner-guard, provider-tier + existing) load without syntax errors at opencode startup
F7. [ ] All 4 skills (`provider-routing`, `perfume-library-query`, `parallel-reader`, `formula-gate` extended) are discoverable via `skill` tool
F8. [ ] `~/.codex/config.toml` is unchanged (Codex DeepLuna stays active)

---

## Disposition Table (locked by user)

| Category | Behavior |
|---|---|
| A.1 OAV physics | HARD block |
| A.2 EU allergens | WARN + auto-substitute suggestion + emit 2 alternative formula versions |
| A.3 Phototoxicity | WARN + FCF substitute suggestion |
| A.3 quant authority | HARD block (claim integrity, not safety) |
| A.4 Receptor saturation | WARN |
| A.5 Composite OAV missing | WARN + inventory substitute suggestion |
| A.6 Oakmoss CoA | DENIED — WARN only, no CoA doc required, recommend Evernyl if >IFRA |
| A.7 VP source | HARD block for release claim, WARN for draft |
| A.8 Sensomics disclaimer | Always appended |
| inventory_stock_contract | HARD block |
| quantitative_authority | HARD block |

---

## Cost Ceiling

Total build cap: ~$1.30 USD (Flash orchestrator + 2× GLM-5.2 max flex final reviews)
Monthly recurring post-build: ~$24 USD

**Codex DeepLuna untouched.**

---

**Implementation owner**: NOT Prometheus (this session is plan-only). The /start-work skill spawns workers via `multi_agent_v1.spawn_agent` (Codex) or `task(subagent_type=...)` (OpenCode) — the planning session lacks that authority by design. Run `/start-work plan-v5-executable-final` from a fresh session with implementation scope.