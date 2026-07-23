# final-audit-polish-v1 - Work Plan

## TL;DR (For humans)

**What you'll get:** A complete audit of every data source, 100+ formulas batch-tested through the pipeline, all gaps fixed, missing ingredient data (hedonic, receptor, biochemical) enriched from published literature, and a systemic weakness report — all gated by the requirement of accumulating 500 independently verified, literature-backed truths.

**Why this approach:** Literature survey and formula testing run in parallel first, then all found gaps are fixed in one remediation wave, then a final logic pass verifies every enriched data point against literature, perfumer knowledge, chemistry, and thermodynamics. The 500-truths target ensures depth — you cannot fabricate your way to 500 cross-verified facts.

**What it will NOT do:** Create new formulas, change the pipeline architecture, add new gates, modify the GUI or backend, touch Docker, or make any change that can't be traced to a published source.

**Effort:** XL (26 tasks across 4 waves, 100+ formula files, PubChem/PubMed for 130+ materials)
**Risk:** Medium — PubChem API rate limits may slow enrichment; pre-existing LSP errors in 5000+ line gates.py are pre-existing and out of scope
**Decisions to sanity-check:** All 100+ formulas batch-tested (not a subset). Triple verification for every fix. Truth count of exactly 500 as stopping condition.

Your next move: approve the plan, or request a high-accuracy review. Full execution detail follows below.

---

> TL;DR (machine): <1 line - effort, risk, deliverables>

## Scope
### Must have
### Must NOT have (guardrails, anti-slop, scope boundaries)

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: <TDD | tests-after | none> + framework
- Evidence: <attemptDir>/task-<N>-final-audit-polish-v1.<ext> (attemptDir = currentAttemptDir from 'omo ulw-loop status --json', .omo/evidence/ulw/<session>/<goalId>/a<attempt>; outside ulw-loop use .omo/evidence/)

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

### Dependency matrix
> C-wave legend: C1=12 (ODT fix), C2=13 (receptor enrich), C3=14 (hedonic fill), C4=15 (biochem enrich), C5=16 (IFRA/phototoxic fix), C6=17 (consistency fix), C7=18 (truth count)
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | — | 12 | 2-8 |
| 2 | — | 13 | 1,3-8 |
| 3 | — | 14 | 1-2,4-8 |
| 4 | — | 15 | 1-3,5-8 |
| 5 | — | 16 | 1-4,6-8 |
| 6 | — | 16 | 1-5,7-8 |
| 7 | — | (truth-only) | 1-6,8 |
| 8 | — | 17 | 1-7 |
| 9 | — | 10 | (parallel with Wave A) |
| 10 | 9 | 11, 19 | — |
| 11 | 10 | 19 | — |
| 12 | 1 | 18 | 13-17 |
| 13 | 2 | 18 | 12,14-17 |
| 14 | 3 | 18 | 12-13,15-17 |
| 15 | 4 | 18 | 12-14,16-17 |
| 16 | 5,6 | 18 | 12-15,17 |
| 17 | 8 | 18 | 12-16 |
| 18 | 12-17 | 19,20,21 | — |
| 19 | 10-11, 18, 1-8 | 22 | 20-21 |
| 20 | 18 | — | 19,21 |
| 21 | 18 | — | 19-20 |
| 22 | 19,20,21 | — | — |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

### Wave A — Literature Survey + Truth Accumulation (parallel with B)

- [ ] 1. Audit ODT_DATA sources — cross-reference every material in `engine/odor_thresholds.py` against published literature
  What to do: For every material with an ODT value, verify the cited source exists and is authoritative. Flag materials with no source. Count sourced vs unsourced entries. For each verified source, record a truth entry.
  Must NOT do: Do not change ODT values — only audit sources. Do not add sources without verification.
  Parallelization: Wave A | Blocked by: — | Blocks: C1
  References: `engine/odor_thresholds.py` ODT_DATA dict, `.opencode/library/perfume_kb.jsonl` odt_* entries, `data/materials/*.yaml` odt_air_ppb/odt_eth_ppm fields
  Acceptance criteria: CSV at `.omo/evidence/odt_source_audit.csv` with columns: material, odt_air, odt_eth, source_cited, source_verified, truth_id. At least 15 truth entries from ODT verification.
  QA scenarios: happy — `wc -l .omo/evidence/odt_source_audit.csv ≥ 100` (at least 100 materials audited); failure — grep for "NO_SOURCE" in CSV and verify each is intentional
  Commit: N | audit only

- [ ] 2. Audit receptor mapping coverage — map every material to known olfactory receptors (OR5AN1, OR5A2, OR10J5, etc.)
  What to do: Search PubChem for each inventory material's known receptor targets. Cross-reference with `engine/pipeline/neuroscience.py` and receptor gates. Record receptor-material pairs as truths.
  Must NOT do: Do not invent receptor mappings without PubChem evidence.
  Parallelization: Wave A | Blocked by: — | Blocks: C2
  References: `engine/pipeline/gates.py` _gate_receptor_saturation (L4101), `engine/pipeline/neuroscience.py`, PubChem `pubchem_get_bioactivity()` for each material CID
  Acceptance criteria: CSV at `.omo/evidence/receptor_map.csv` with: material, receptor, pubchem_cid, evidence_type, truth_id. At least 20 receptor-material pairs verified.
  QA scenarios: happy — ≥20 pairs in CSV with non-null pubchem_cid; failure — verify all pairs have PubChem evidence
  Commit: N | audit only

- [ ] 3. Audit hedonic/valence data — count hedonic coverage, fill gaps from literature
  What to do: Count `hedonic_valence` field population in `data/materials/*.yaml` and `engine/ingredient_intelligence.py`. For gaps, search PubChem/PubMed. Record each verified hedonic value as truth.
  Must NOT do: Do not fabricate hedonic values — mark as "unknown" if no literature found.
  Parallelization: Wave A | Blocked by: — | Blocks: C3
  References: `data/materials/*.yaml` hedonic_valence field, `engine/ingredient_intelligence.py` _PROFILES, PubChem, PubMed
  Acceptance criteria: CSV at `.omo/evidence/hedonic_audit.csv` with: material, hedonic_valence_current, literature_found, source, truth_id. Hedonic coverage improved from baseline.
  QA scenarios: happy — hedonic coverage count documented; failure — any fabricated value detected
  Commit: N | audit only

- [ ] 4. Audit biochemical/neurotransmitter data — search for dopamine, serotonin, GABA, psychoactive effects per material
  What to do: For each inventory material, search PubChem for pharmacological actions, neurotransmitter interactions, psychoactive classifications. Cross-reference with `engine/pipeline/neuroscience.py` _PSYCHOACTIVE_EFFECTS.
  Must NOT do: Do not make medical claims. Mark all as "research only — not medical advice."
  Parallelization: Wave A | Blocked by: — | Blocks: C4
  References: `engine/pipeline/neuroscience.py`, PubChem `pubchem_get_bioactivity()`, PubMed
  Acceptance criteria: CSV at `.omo/evidence/biochem_audit.csv` with: material, neurotransmitter_target, evidence, pubchem_cid, truth_id. At least 10 verified neuro/biochem findings.
  QA scenarios: happy — ≥10 verified entries; failure — any entry without PubChem CID
  Commit: N | audit only

- [ ] 5. Audit IFRA/allergen coverage — verify EU 2023/1545 82-allergen list completeness, IFRA limit population
  What to do: Read `.opencode/library/eu_2023_1545_allergens.json` — count entries vs required 82. Read `data/materials/*.yaml` — count ifra_max_pct_edp population. Cross-reference against IFRA 51st Amendment.
  Must NOT do: Do not modify IFRA limits without authoritative source.
  Parallelization: Wave A | Blocked by: — | Blocks: C5
  References: `.opencode/library/eu_2023_1545_allergens.json`, `data/materials/*.yaml` ifra_max_pct_edp, `engine/pipeline/gates.py` _gate_eu_allergen_declaration (L3931)
  Acceptance criteria: Report at `.omo/evidence/ifra_audit.md` with: allergen_count (must be 82), ifra_coverage_pct, gaps list. At least 5 truths from IFRA/allergen verification.
  QA scenarios: happy — allergen_count == 82; failure — any missing EU 2023/1545 allergen
  Commit: N | audit only

- [ ] 6. Audit phototoxicity database completeness — verify all known phototoxic oils are listed
  What to do: Read `.opencode/library/phototoxic_oils.json` — count entries. Cross-reference against known phototoxic oils (bergamot, lime expressed, lemon cold-pressed, grapefruit, bitter orange, angelica root, rue, cumin, parsley leaf, etc.). Flag missing entries.
  Must NOT do: Do not change bergaptene/IFRA values without authoritative source.
  Parallelization: Wave A | Blocked by: — | Blocks: C5
  References: `.opencode/library/phototoxic_oils.json`, `engine/pipeline/gates.py` _gate_phototoxic_furanocoumarin (L4042), IFRA standards
  Acceptance criteria: JSON patch file at `.omo/evidence/phototoxic_gaps.json` listing missing oils. At least 3 truths from phototoxic verification.
  QA scenarios: happy — all known phototoxic oils listed or flagged as missing with reason; failure — bergamot missing from list
  Commit: N | audit only

- [ ] 7. Audit VP source hierarchy — verify vp_source field population, flag NIST/EPI gaps
  What to do: Read `data/materials/*.yaml` — count vp_source population (should be 1262 entries from earlier work). Identify materials needing NIST/EPI/PubChem_exp verification. Record VP source truths.
  Must NOT do: Do not change VP values.
  Parallelization: Wave A | Blocked by: — | Blocks: C6
  References: `data/materials/*.yaml` vp_source field, `.opencode/cache/vp_source_audit.csv`, NIST Chemistry WebBook, PubChem
  Acceptance criteria: Report at `.omo/evidence/vp_source_report.md` with: total_materials, sourced_count, NIST_count, EPI_count, PubChem_count, UNKNOWN_count. At least 10 truths from VP source verification.
  QA scenarios: happy — sourced_count ≥ 200; failure — any vp_source still null after audit
  Commit: N | audit only

- [ ] 8. Cross-reference internal data consistency — inventory.txt vs YAML vs _PROFILES vs ODT_DATA
  What to do: For every material in inventory.txt, verify it exists in all 4 required data locations with consistent values. Flag mismatches in name, dilution, VP, ODT.
  Must NOT do: Do not fix inconsistencies — only flag them for Wave C.
  Parallelization: Wave A | Blocked by: — | Blocks: C1-C6
  References: `inventory.txt`, `data/materials/*.yaml`, `engine/ingredient_intelligence.py` _PROFILES, `engine/odor_thresholds.py` ODT_DATA
  Acceptance criteria: CSV at `.omo/evidence/consistency_audit.csv` with: material, in_inventory, in_yaml, in_profiles, in_odt, vp_match, odt_match, name_match. At least 10 truths from consistency verification.
  QA scenarios: happy — ≥130 materials audited; failure — any inventory material missing from all 4 without explanation
  Commit: N | audit only

### Wave B — Pipeline Mass Testing (parallel with A)

- [ ] 9. Build batch-testing script for ALL formula files
  What to do: Write `scripts/batch_gate_all_formulas.py` — iterates ALL .md files in `formulas/`, runs `scripts/formula_release_gate.py` for each, collects results. Skip non-formula files (_ prefixed, prep_, analysis files). Handle gate failures gracefully (don't stop on first failure).
  Must NOT do: Do not modify any formula files. Write outputs to `.omo/evidence/batch_results/`.
  Parallelization: Wave B | Blocked by: — | Blocks: B2
  References: `scripts/formula_release_gate.py` CLI, `formulas/*.md` (100+ files)
  Acceptance criteria: Script runs `python scripts/batch_gate_all_formulas.py --brief generic` and processes ≥80 formula files (excluding non-formulas). Exit code 0 even if formulas fail.
  QA scenarios: happy — script runs `python scripts/batch_gate_all_formulas.py --subset 5` (first on 5 test formulas), all 5 produce valid JSON → then run full set, ≥80 formula files gated; failure — any formula produces invalid JSON or script hangs (add 60s timeout per formula)
  Commit: N | script is temporary batch tool

- [ ] 10. Execute batch test — run ALL formula files through pipeline
  What to do: Execute `python scripts/batch_gate_all_formulas.py --brief generic --json --output-dir .omo/evidence/batch_results/`. Collect pass/fail/warn per formula, per gate.
  Must NOT do: Do not stop on failures — collect ALL results.
  Parallelization: Wave B | Blocked by: B1 | Blocks: B3, D1
  References: `scripts/batch_gate_all_formulas.py`, `scripts/formula_release_gate.py`
  Acceptance criteria: `.omo/evidence/batch_results/summary.json` with: total_formulas, passed, failed, warned, failed_gates per formula. ≥80 formulas processed.
  QA scenarios: happy — summary.json exists with ≥80 formulas; failure — less than 50 formulas processed (check script)
  Commit: Y | feat(batch): batch gate result summary

- [ ] 11. Analyze batch results — categorize failures by gate, material, family
  What to do: Parse `summary.json` — group failures by gate name (IFRA, OAV, pyramid, etc.), by fragrance family, by common missing materials. Produce prioritized fix list for Wave C.
  Must NOT do: Do not start fixing — only categorize for Wave C.
  Parallelization: Wave B | Blocked by: B2 | Blocks: C1-C6
  References: `.omo/evidence/batch_results/summary.json`, `engine/families/registry.py` ARCHETYPES
  Acceptance criteria: Report at `.omo/evidence/batch_analysis.md` with: top 10 failing gates, top 10 fragile formulas, top 10 missing/problematic materials. Prioritized fix list.
  QA scenarios: happy — report has 3 ranked lists; failure — no failures found (unlikely but verify correctness)
  Commit: N | analysis only

### Wave C — Gap Remediation + Data Enrichment (after A)

- [ ] 12. Fix ODT source gaps — add missing citations to odor_thresholds.py
  What to do: From A1 audit, add `sources` field to ODT_DATA entries that lack it. Source must be verified against published literature. Do not change values.
  Must NOT do: Do not change numeric ODT values. Do not add sources you cannot verify.
  Parallelization: Wave C | Blocked by: A1 | Blocks: —
  References: `.omo/evidence/odt_source_audit.csv`, PubMed/Google Scholar for each material, `engine/odor_thresholds.py`
  Acceptance criteria: ODT source coverage improves from baseline. Test: `python -c "from engine.odor_thresholds import ODT_DATA; print(len([v for v in ODT_DATA.values() if v.get('sources')]))"` shows increase.
  QA scenarios: happy — source coverage count increases; failure — any ODT value changed (check git diff)
  Commit: Y | fix(odt): add verified literature sources to ODT_DATA

- [ ] 13. Enrich receptor mappings from PubChem
  What to do: From A2 audit gaps, query PubChem for missing receptor-material pairs. Add to `engine/pipeline/neuroscience.py` or receptor gate data. Record truths.
  Must NOT do: Do not add receptor mappings without PubChem evidence (CID required).
  Parallelization: Wave C | Blocked by: A2 | Blocks: —
  References: `.omo/evidence/receptor_map.csv`, PubChem API, `engine/pipeline/gates.py` _gate_receptor_saturation
  Acceptance criteria: Receptor coverage count increases. Test: verify new entries have non-null CIDs.
  QA scenarios: happy — receptor count ≥20 more than baseline; failure — any entry without CID
  Commit: Y | feat(receptor): enrich receptor mapping from PubChem

- [ ] 14. Fill hedonic valence gaps from literature
  What to do: From A3 audit, fill hedonic_valence for materials where literature data exists. Source must be cited. Mark unfillable as "unknown" explicitly.
  Must NOT do: Do not fabricate hedonic values.
  Parallelization: Wave C | Blocked by: A3 | Blocks: —
  References: `.omo/evidence/hedonic_audit.csv`, PubChem, PubMed, `data/materials/*.yaml`
  Acceptance criteria: Hedonic coverage % increases. Test: compare before/after counts.
  QA scenarios: happy — hedonic coverage improves; failure — any fabricated value without citation
  Commit: Y | feat(hedonic): enrich hedonic valence data from literature

- [ ] 15. Enrich biochemical/neurotransmitter data
  What to do: From A4 audit, add verified neurotransmitter/biochemical interactions to data. Include PubChem CID and evidence class.
  Must NOT do: No medical claims. All entries marked as "research only."
  Parallelization: Wave C | Blocked by: A4 | Blocks: —
  References: `.omo/evidence/biochem_audit.csv`, PubChem, `engine/pipeline/neuroscience.py`
  Acceptance criteria: Biochem coverage count increases. Test: verify new entries have CIDs.
  QA scenarios: happy — ≥5 new verified entries; failure — any entry without evidence
  Commit: Y | feat(biochem): enrich neuro/biochem data from PubChem

- [ ] 16. Fix IFRA and phototoxic gaps
  What to do: From A5/A6 audits, add missing EU 2023/1545 allergens, fill ifra_max_pct_edp for materials with known IFRA limits, add missing phototoxic oils. Source: IFRA 51st Amendment, EU 2023/1545.
  Must NOT do: Do not change existing IFRA limits without authoritative source. Do not make safety certifications.
  Parallelization: Wave C | Blocked by: A5, A6 | Blocks: —
  References: `.omo/evidence/ifra_audit.md`, `.omo/evidence/phototoxic_gaps.json`, IFRA standards
  Acceptance criteria: EU 2023/1545 allergen count == 82. Phototoxic oil count covers all known phototoxic oils.
  QA scenarios: happy — allergen count 82, no known phototoxic oil missing; failure — bergamot missing from phototoxic list
  Commit: Y | fix(safety): fill IFRA and phototoxic data gaps

- [ ] 17. Fix internal data consistency
  What to do: From A8 audit, fix all name mismatches, dilution discrepancies, VP conflicts, and ODT drifts between the 4 data sources. Rebuild material_properties.json and perfume_kb.jsonl after fixes.
  Must NOT do: Do not change values without verifying which source is authoritative.
  Parallelization: Wave C | Blocked by: A8 | Blocks: —
  References: `.omo/evidence/consistency_audit.csv`, `inventory.txt`, `data/materials/*.yaml`, `engine/ingredient_intelligence.py`, `engine/odor_thresholds.py`
  Acceptance criteria: All inventory materials present in all 4 data sources. Rebuild script runs clean: `python _generate_material_properties.py` and `python scripts/build_perfume_kb.py` exit 0.
  QA scenarios: happy — rebuild succeeds, consistency audit shows 0 mismatches; failure — any rebuild error
  Commit: Y | fix(data): resolve cross-source data inconsistencies

- [ ] 18. Run truth count verification — ensure ≥500 truths accumulated
  What to do: Count all truth entries from `.omo/evidence/truths.jsonl`. If <500, return to Wave A audits for ONE retry pass (re-run only the highest-yield audit from todos 1-8). If still <500 after retry, document the gap in the weakness report (todo 19) and proceed — do NOT loop beyond one retry. Maximum: 1 retry pass.
  Must NOT do: Do not fabricate truths to reach 500. Do not exceed one retry pass. Do not stop before attempting the retry.
  Parallelization: Wave C | Blocked by: C1-C6 | Blocks: D1
  References: `.omo/evidence/truths.jsonl`, all A* audit CSVs
  Acceptance criteria: `wc -l .omo/evidence/truths.jsonl ≥ 500`. Each line is valid JSON with: id, description, literature_source, codebase_evidence, crosscheck_sources (≥2), verified_at.
  QA scenarios: happy — ≥500 valid truths; failure — <500 truths or any truth with <2 sources
  Commit: N | verification only

### Wave D — Weakness Report + Finishing Touches (after A,B,C)

- [ ] 19. Compile systemic weakness report
  What to do: From all Wave A audits (todos 1-8) and Wave B batch results (todo 11), identify systemic weaknesses: data domains with chronic low coverage, gate types that most commonly fail, material categories most frequently missing data, architectural patterns that cause fragility.
  Must NOT do: Do not sugarcoat — honest weakness assessment.
  Parallelization: Wave D | Blocked by: B3, C7 | Blocks: D2
  References: `.omo/evidence/batch_analysis.md`, all audit CSVs, `engine/pipeline/gates.py`
  Acceptance criteria: Report at `.omo/evidence/weakness_report.md` with: top 5 systemic weaknesses, root cause per weakness, recommended fix (effort: Low/Medium/High), impact if unfixed. At least 3 weaknesses must have concrete remediation paths.
  QA scenarios: happy — report has ≥3 weaknesses with root causes and fixes; failure — report is generic ("needs more data") without specifics
  Commit: Y | docs: systemic weakness report

- [ ] 20. Final logic pass — verify all enriched data passes literature/perfumer/chemistry/thermo validation
  What to do: For every enriched data point from Wave C, run triple validation: (1) literature — source verified and cited, (2) perfumer logic — consistent with known perfume families and odor character, (3) chemistry/thermo — VP hierarchy consistent, OAV plausible, receptor mappings chemically sensible.
  Must NOT do: Do not skip any enriched data point. If a data point fails any check, flag it — do not silently remove.
  Parallelization: Wave D | Blocked by: C1-C6 | Blocks: —
  References: All enriched YAML fields, `.omo/evidence/truths.jsonl`, `engine/odor_thresholds.py`, `engine/ingredient_intelligence.py`
  Acceptance criteria: Report at `.omo/evidence/logic_pass.md` with: total_enriched, passed, failed, failed_details. Every failure must have explanation. Overall pass rate ≥ 90%.
  QA scenarios: happy — pass rate ≥90%; failure — any enriched value contradicts known chemistry
  Commit: N | verification only

- [ ] 21. Pipeline end-to-end verification — re-run 5 core formulas after all fixes
  What to do: Re-run 5 diverse formulas (Prada L'Homme, Vetiver Classique, Osmanthus Explorer, Rose Chypre, Tuberose Floral) through `scripts/formula_release_gate.py` after all Wave C fixes. Verify gates pass or warn (no unexpected FAILs).
  Must NOT do: Do not run all 100 again — 5 representative formulas is sufficient for verification.
  Parallelization: Wave D | Blocked by: C1-C6 | Blocks: —
  References: `scripts/formula_release_gate.py`, 5 representative formula files
  Acceptance criteria: All 5 formulas gate successfully (PASS or expected WARNs only, no unexpected FAILs). Results at `.omo/evidence/final_gate_results/`.
  QA scenarios: happy — all 5 formulas pass with ≤2 unexpected WARNs; failure — any formula FAILs on a gate that should pass
  Commit: N | verification only

- [ ] 22. Cleanup and finalize — remove temp files, verify git status clean
  What to do: Remove temporary audit CSVs from `.omo/evidence/` that were consolidated into final reports. Verify `git status` shows only intentional changes. Run `python -m py_compile` on all modified Python files.
  Must NOT do: Do not remove evidence files that support truths or final reports. Do not commit temp files.
  Parallelization: Wave D | Blocked by: D1, D2, D3 | Blocks: —
  References: `.omo/evidence/` directory, git status
  Acceptance criteria: `git status` shows only: plan files in .omo/, enriched YAML files, enriched engine/ files, evidence reports (not temp CSVs). All modified .py files compile.
  QA scenarios: happy — git status clean of unexpected changes; failure — temp files committed or .py files fail compile
  Commit: Y | chore: cleanup temp files and finalize

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — verify every todo (1-22) has been executed and its QA evidence written. `grep -c '"status": "PASS"' .omo/evidence/*.json` shows ≥22 passing checks.
- [ ] F2. Code quality review — `python -m py_compile` on all modified .py files exits 0; `git diff --stat` shows no deleted tests, no reverted fixes.
- [ ] F3. Real manual QA — re-run `scripts/formula_release_gate.py` on 3 diverse formulas; all gate with PASS or expected WARNs only; output captured to `.omo/evidence/final_qa/`.
- [ ] F4. Scope fidelity — verify no new formulas created, no new gates added, no GUI/backend/Docker changes; truth count in `.omo/evidence/truths.jsonl` is ≥500 and every truth has ≥2 sources.

## Commit strategy

## Success criteria
