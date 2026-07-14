# pipeline-improvement - Work Plan

## TL;DR (For humans)

**What you'll get:** A more accurate, less noisy pipeline that correctly scores formulas, removes 17 dead warning gates, fixes hardcoded longevity claims, enables mixture-suppression physics, and adds dose-reduction recommendations.

**Why this approach:** Prioritized by user-visible impact (scoring/output fixes first), then physics accuracy (ethanol in mole fractions, mixture-shifted ODT), then infrastructure (gate cleanup, intervention engine). All changes preserve JSON output schema for backward compatibility.

**What it will NOT do:** Will not create new pipeline scripts (RULE 2), will not modify backend/frontend, will not add new fragrance families, will not change inventory data files.

**Effort:** XL (5 waves, ~30 todos, 3-4 days of focused work)
**Risk:** Medium - physics changes (Wave 3) need regression tests to avoid breaking existing formulas
**Decisions I made for you:**
- Mixture-shifted ODT enabled by default (already implemented, just never called)
- Skeleton OAV threshold raised to 1.0 (sub-threshold markers shouldn't pass)
- Scoring axes renamed with deprecation aliases (lift→top_dominance, character→family_alignment, versatility→oav_balance)
- Gate phasing: 5 phases with short-circuit on FAIL in early phases
- Cost output added to analysis using existing sparse price_data
- Longevity computed from temporal profile instead of hardcoded string
- Ethanol included in mole fractions (70-80% of product was excluded)
- UNIFAC implementation deferred to future work (major refactor); keep Hansen heuristic as fallback

Your next move: Review the plan below. If approved, execute with `$start-work`. Full execution detail follows.

---

> TL;DR (machine): XL effort, Medium risk, 30 todos across 5 waves fixing scoring/output/physics/interventions/architecture

## Scope
### Must have
- Remove 17 dead future_modules gates (always WARN, never useful)
- Fix hardcoded "Est. skin life: 6-8h" string literal
- Fix block balance substring matching (everything not citrus/base = "floral")
- Fix skeleton OAV threshold from 0.5 to 1.0
- Fix `_safe_gate()` to log tracebacks instead of silently swallowing errors
- Fix shelf life temperature inconsistency (hardcoded 295K vs config 305K)
- Recalibrate 8 misnamed/miscalibrated industry_10 scores
- Enable mixture-shifted ODT in pipeline main path
- Add ethanol to mole fractions in FormulaState
- Add dose-reduction path to intervention engine
- Fix perturbation floor bias for trace materials
- Add cost output to analysis

### Must NOT have (guardrails, anti-slop, scope boundaries)
- No new pipeline scripts (RULE 2: never create new pipeline scripts)
- No changes to backend/ FastAPI app (separate concern)
- No frontend changes
- No new fragrance family archetypes (separate concern)
- No changes to inventory.txt or data/materials/*.yaml (data entry, not pipeline logic)
- No breaking changes to JSON output schema (use deprecation aliases for renamed fields)
- No UNIFAC/HANNA integration (deferred to future work — major refactor)
- No competitive binding model (deferred — new physics layer)

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD for physics changes (Wave 3), tests-after for gate/scoring fixes (Waves 1-2, 4-5)
- Evidence: .omo/evidence/task-<N>-pipeline-improvement.<ext>
- Regression: All existing tests in tests/test_pipeline_*.py must remain green
- Manual QA: Run `python scripts/formula_release_gate.py --formula-file formulas/test_formula.md --brief generic --print-analysis` after each wave

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

**Wave 1: Quick wins (high impact, low effort)** — 6 todos, all independent, can run in parallel
**Wave 2: Scoring recalibration** — 8 todos, mostly independent, some depend on Wave 1 gate cleanup
**Wave 3: Physics improvements** — 5 todos, sequential (ethanol → mixture-shifted ODT → temperature)
**Wave 4: Intervention engine** — 5 todos, independent except dose-reduction depends on scoring fixes
**Wave 5: Architecture & output** — 6 todos, depends on Waves 1-4 completion

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1.1-1.6 (Wave 1) | None | 2.1-2.8 | All Wave 1 todos |
| 2.1-2.8 (Wave 2) | 1.1 (dead gate removal) | 4.4 (dose-reduction) | All Wave 2 todos |
| 3.1-3.5 (Wave 3) | None | None | Sequential within wave |
| 4.1-4.5 (Wave 4) | 2.1-2.8 (scoring fixes) | None | All Wave 4 todos |
| 5.1-5.6 (Wave 5) | 1.1-1.6, 2.1-2.8, 4.1-4.5 | None | All Wave 5 todos |

## Todos
> Implementation + Test = ONE todo. Never separate.

### Wave 1: Quick wins (high impact, low effort)

- [ ] 1.1. Remove 17 dead future_modules gates
  **What to do:** In `engine/pipeline/gates.py`, wrap all 17 future_modules gate registrations (lines 4588-4611) in a conditional block that checks `_FUTURE_MODULES_AVAILABLE`. If False, skip all 17 gates entirely (don't register them in the gates list). This removes the persistent WARN noise.
  **Must NOT do:** Do not delete the gate functions themselves (they may be useful if future_modules is ever installed). Do not change the gate function signatures.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:4588-4611` (gate registrations), `engine/pipeline/oav_intelligence.py:16` (`_FUTURE_MODULES_AVAILABLE = False`)
  **Acceptance criteria:** Run `python scripts/formula_release_gate.py --formula-file formulas/test_formula.md --brief generic --json 2>/dev/null | jq '.gates | length'` — gate count should decrease by 17. Run `grep -c "future_modules" output.json` — should return 0.
  **QA scenarios:**
  - Happy: `python -m pytest tests/test_pipeline_gates.py -v` — all tests pass, no future_modules gates in output
  - Failure: If `_FUTURE_MODULES_AVAILABLE = True`, gates should still register (test with mock import)
  **Evidence:** .omo/evidence/task-1.1-pipeline-improvement.json (gate count before/after)
  **Commit:** Y | refactor(pipeline): remove 17 dead future_modules gates when unavailable

- [ ] 1.2. Fix hardcoded "Est. skin life: 6-8h" string literal
  **What to do:** In `scripts/format_pipeline_analysis.py:272`, replace the hardcoded string with a computed longevity estimate from the temporal profile data. Use the formula: `longevity_hr = (base_oav_at_4hr / base_oav_at_opening) * 8.0` (heuristic: if 50% of base OAV remains at 4hr, estimate 8hr total skin life). Format as `f"Est. skin life: {longevity_hr:.0f}h moderate + {longevity_hr*0.5:.0f}h skin scent"`.
  **Must NOT do:** Do not hardcode any specific hour values. Do not assume all formulas have 6-8h longevity.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `scripts/format_pipeline_analysis.py:272` (hardcoded string), `engine/pipeline/simulator.py:20-26` (DEFAULT_WINDOWS), `engine/optimizer/scoring.py:1091-1096` (longevity_hr scoring)
  **Acceptance criteria:** Run pipeline on a citrus-heavy formula (90% top notes) — output should show <4h longevity. Run on a musk-heavy formula (80% base) — output should show >10h longevity.
  **QA scenarios:**
  - Happy: `python scripts/formula_release_gate.py --formula-file formulas/citrus_test.md --brief generic --print-analysis` — longevity < 4h
  - Failure: If temporal data missing, fallback to "Est. skin life: data insufficient" (not hardcoded 6-8h)
  **Evidence:** .omo/evidence/task-1.2-pipeline-improvement.txt (analysis output excerpts)
  **Commit:** Y | fix(analysis): compute longevity from temporal profile instead of hardcoded string

- [ ] 1.3. Fix block balance substring matching
  **What to do:** In `scripts/format_pipeline_analysis.py:365-369`, replace hardcoded citrus/base substring checks with profile-based note/role lookup. For each material, check `m.get("note")` (top/heart/base) and `m.get("family")` from the MaterialState. Compute `citrus_oav = sum(oav for m in materials if m["note"] == "top" and m["family"] == "citrus")`, `base_oav = sum(oav for m in materials if m["note"] == "base")`, `floral_oav = sum(oav for m in materials if m["note"] == "heart" and m["family"] in {"floral", "musk", "amber"})`.
  **Must NOT do:** Do not use substring matching on material names. Do not assume "floral" = everything not citrus/base.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `scripts/format_pipeline_analysis.py:365-369` (hardcoded substrings), `engine/pipeline/formula_state.py:61-92` (MaterialState fields: note, family)
  **Acceptance criteria:** Run pipeline on a formula with "Methyl Pamplemousse" — should be classified as citrus (note=top, family=citrus). Run on "Kephalis" — should be classified as base (note=base, family=wood).
  **QA scenarios:**
  - Happy: `python scripts/formula_release_gate.py --formula-file formulas/methyl_pamplemousse_test.md --brief generic --print-analysis` — Methyl Pamplemousse in citrus_oav
  - Failure: If note/family missing from MaterialState, fallback to "unknown" category (not "floral")
  **Evidence:** .omo/evidence/task-1.3-pipeline-improvement.txt (block balance output)
  **Commit:** Y | fix(analysis): use profile-based note/family for block balance instead of substring matching

- [ ] 1.4. Fix skeleton OAV threshold from 0.5 to 1.0
  **What to do:** In `engine/pipeline/gates.py:3096`, change the skeleton marker perceptibility threshold from `oav >= 0.5` to `oav >= 1.0`. This ensures skeleton markers are functionally perceptible (OAV 1.0 is the perceptible threshold per RULE 1).
  **Must NOT do:** Do not change the skeleton marker logic beyond the threshold. Do not modify the `_SKELETONS` dict.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:3096` (threshold check), `engine/perception/oav.py:7-10` (OAV perceptibility bands: OAV < 1 = not perceptible)
  **Acceptance criteria:** Run `python -m pytest tests/test_pipeline_gates.py::test_fougere_skeleton -v` — test should still pass. Create a test formula with a skeleton marker at OAV=0.7 — skeleton gate should FAIL (marker not perceptible).
  **QA scenarios:**
  - Happy: Formula with lavender at OAV=5.0 → fougère skeleton PASS
  - Failure: Formula with lavender at OAV=0.7 → fougère skeleton FAIL (marker sub-threshold)
  **Evidence:** .omo/evidence/task-1.4-pipeline-improvement.json (gate output)
  **Commit:** Y | fix(pipeline): raise skeleton OAV threshold to 1.0 for functional perceptibility

- [ ] 1.5. Fix `_safe_gate()` to log tracebacks
  **What to do:** In `engine/pipeline/gates.py:199-211`, modify `_safe_gate()` to log the full traceback before converting exceptions to WARN. Add a `traceback` field to the GateResult data dict: `data={"error": str(e), "traceback": traceback.format_exc()}`. Import `traceback` at the top of the file.
  **Must NOT do:** Do not change the exception handling logic (still convert to WARN). Do not remove the `_safe_gate()` wrapper.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:199-211` (_safe_gate implementation), `engine/pipeline/gates.py:193-196` (_result helper)
  **Acceptance criteria:** Create a test gate that raises `ValueError("test error")` — GateResult should have `data.traceback` field containing "ValueError: test error".
  **QA scenarios:**
  - Happy: Normal gate → PASS/WARN/FAIL with no traceback field
  - Failure: Gate raises KeyError → WARN with `data.traceback` showing full stack trace
  **Evidence:** .omo/evidence/task-1.5-pipeline-improvement.json (gate result with traceback)
  **Commit:** Y | fix(pipeline): log tracebacks in _safe_gate() for debugging

- [ ] 1.6. Fix shelf life temperature inconsistency
  **What to do:** In `engine/pipeline/gates.py:462` and `gates.py:543-544`, replace hardcoded `T_K=295.0` with `config.temperature_K` (which defaults to 305.0 for Bangkok ambient). This ensures shelf life prediction uses the same temperature as the rest of the pipeline.
  **Must NOT do:** Do not change the shelf life calculation logic beyond the temperature parameter.
  **Parallelization:** Wave 1 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:462` (hardcoded 295K), `engine/pipeline/gates.py:543-544` (hardcoded 295K), `engine/pipeline/gates.py:118` (ReleaseGateConfig.temperature_K = 305.0)
  **Acceptance criteria:** Run pipeline with `--temperature-k 310` — shelf life prediction should use 310K, not 295K. Grep output for "295.0" should return 0 matches in gates.py.
  **QA scenarios:**
  - Happy: `python scripts/formula_release_gate.py --formula-file formulas/test.md --temperature-k 310 --json` — shelf life uses 310K
  - Failure: If config.temperature_K is None, fallback to 305.0 (not 295.0)
  **Evidence:** .omo/evidence/task-1.6-pipeline-improvement.json (shelf life calculation)
  **Commit:** Y | fix(pipeline): use config.temperature_K for shelf life instead of hardcoded 295K

### Wave 2: Scoring recalibration

- [ ] 2.1. Fix `impact` score (separate opening from total)
  **What to do:** In `engine/pipeline/release_scoring.py:83-87`, replace `opening_oav = total_oav` with `opening_oav = sum(float(row.oav or 0.0) for row in percept if row.note == "top")`. This measures actual opening impact (top-note OAV) instead of total formula OAV.
  **Must NOT do:** Do not change the log10 scaling formula. Do not rename the field (keep "impact" for backward compatibility).
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:83-87` (impact calculation), `engine/pipeline/formula_state.py:61-92` (MaterialState.note field)
  **Acceptance criteria:** Formula with 90% top-note OAV → impact > 80. Formula with 10% top-note OAV → impact < 30.
  **QA scenarios:**
  - Happy: Citrus-heavy formula (90% top) → impact = 85
  - Failure: Base-heavy formula (10% top) → impact = 15 (not 70 from total OAV)
  **Evidence:** .omo/evidence/task-2.1-pipeline-improvement.json (impact scores)
  **Commit:** Y | fix(scoring): separate opening impact from total OAV

- [ ] 2.2. Fix `tenacity` score (base-only, not heart+base)
  **What to do:** In `engine/pipeline/release_scoring.py:84,88`, change `base_oav = sum(...if row.note in {"base", "heart"})` to `base_oav = sum(...if row.note == "base")`. Recalibrate the factor from 150.0 to 130.0 so that 67% base OAV → 87/100 (high but not max).
  **Must NOT do:** Do not include heart materials in tenacity calculation.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:84,88` (tenacity calculation)
  **Acceptance criteria:** Formula with 67% base OAV, 0% heart → tenacity = 87. Formula with 0% base, 67% heart → tenacity = 0.
  **QA scenarios:**
  - Happy: Musk-heavy formula (70% base) → tenacity = 91
  - Failure: Floral-heavy formula (70% heart, 0% base) → tenacity = 0 (not 100)
  **Evidence:** .omo/evidence/task-2.2-pipeline-improvement.json (tenacity scores)
  **Commit:** Y | fix(scoring): use base-only OAV for tenacity, recalibrate factor

- [ ] 2.3. Fix `diffusion` score (use actual physics, not material count)
  **What to do:** In `engine/pipeline/release_scoring.py:89`, replace `diffusion = min(100.0, n_percept * 6.0 + 10.0)` with a physics-based metric: `diffusion = min(100.0, total_vapor_ppm / 100.0)` where `total_vapor_ppm = sum(row.vapor_ppm for row in percept)`. This measures actual headspace concentration, not material count.
  **Must NOT do:** Do not use material count as a proxy for diffusion.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:89` (diffusion calculation), `engine/pipeline/formula_state.py:148-149` (total_vapor_ppm property)
  **Acceptance criteria:** Formula with 3 materials at OAV 50,000 → diffusion > 80. Formula with 30 materials at OAV 1 → diffusion < 30.
  **QA scenarios:**
  - Happy: High-impact formula (total_vapor_ppm = 8000) → diffusion = 80
  - Failure: Low-impact formula (total_vapor_ppm = 500) → diffusion = 5
  **Evidence:** .omo/evidence/task-2.3-pipeline-improvement.json (diffusion scores)
  **Commit:** Y | fix(scoring): use vapor concentration for diffusion instead of material count

- [ ] 2.4. Rename `lift` to `top_dominance` (with deprecation alias)
  **What to do:** In `engine/pipeline/release_scoring.py:96,156`, rename the field from "lift" to "top_dominance". Add a deprecation alias: `industry_10["lift"] = industry_10["top_dominance"]` for backward compatibility. Invert the score: `top_dominance = 100.0 - min(100.0, top_oav / total_oav * 100.0)` so higher = more balanced (less top-heavy).
  **Must NOT do:** Do not remove the "lift" field entirely (backward compatibility).
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:96,156` (lift calculation and output)
  **Acceptance criteria:** Formula with 85% top OAV → top_dominance = 15 (low = top-heavy). JSON output should have both "top_dominance" and "lift" fields with same value.
  **QA scenarios:**
  - Happy: Balanced formula (25% top) → top_dominance = 75
  - Failure: Top-heavy formula (85% top) → top_dominance = 15 (not 85)
  **Evidence:** .omo/evidence/task-2.4-pipeline-improvement.json (top_dominance scores)
  **Commit:** Y | refactor(scoring): rename lift→top_dominance, invert for clarity

- [ ] 2.5. Rename `character` to `family_alignment` (with deprecation alias)
  **What to do:** In `engine/pipeline/release_scoring.py:151`, replace `scores.get("photorealism", 50.0)` with a family alignment score from `engine.optimizer.scoring.FormulaScorer.score_family_alignment()`. Add deprecation alias: `industry_10["character"] = industry_10["family_alignment"]`.
  **Must NOT do:** Do not use photorealism as a proxy for family alignment.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:151` (character calculation), `engine/optimizer/scoring.py:2193-2264` (score_family_alignment method)
  **Acceptance criteria:** Chypre formula with correct chypre skeleton → family_alignment > 80. Chypre formula with wrong skeleton → family_alignment < 40.
  **QA scenarios:**
  - Happy: Well-aligned fougère → family_alignment = 85
  - Failure: Misaligned fougère (missing lavender) → family_alignment = 30
  **Evidence:** .omo/evidence/task-2.5-pipeline-improvement.json (family_alignment scores)
  **Commit:** Y | refactor(scoring): rename character→family_alignment, use actual family scoring

- [ ] 2.6. Fix `temporal_coherence` (don't penalize linear formulas)
  **What to do:** In `engine/pipeline/release_scoring.py:99-112`, add a style-aware modifier: if `mean_delta < 0.05` (nearly linear), set `temporal_coherence = 100.0` (intentionally linear is good). Otherwise, keep the existing formula.
  **Must NOT do:** Do not remove the coefficient of variation calculation for non-linear formulas.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:99-112` (temporal_coherence calculation)
  **Acceptance criteria:** Linear skin-scent formula (mean_delta = 0.02) → temporal_coherence = 100. Evolving formula (mean_delta = 0.5, std_delta = 0.1) → temporal_coherence = 70.
  **QA scenarios:**
  - Happy: Intentionally linear formula → temporal_coherence = 100
  - Failure: Chaotic formula (high std/mean ratio) → temporal_coherence < 50
  **Evidence:** .omo/evidence/task-2.6-pipeline-improvement.json (temporal_coherence scores)
  **Commit:** Y | fix(scoring): don't penalize intentionally linear formulas in temporal_coherence

- [ ] 2.7. Rename `versatility` to `oav_balance` (with deprecation alias)
  **What to do:** In `engine/pipeline/release_scoring.py:123-127,155`, rename the field from "versatility" to "oav_balance". Use perceptible-only OAVs for the min value: `min_oav = min(oavs) if oavs else 1.0` (already filtered at line 79-81). Add deprecation alias.
  **Must NOT do:** Do not include sub-threshold materials (OAV < 1) in the range calculation.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:123-127,155` (versatility calculation)
  **Acceptance criteria:** Formula with OAV range 1-1000 → oav_balance = 55. Formula with OAV range 1-1,000,000 → oav_balance = 10.
  **QA scenarios:**
  - Happy: Balanced formula (OAV 5-500) → oav_balance = 70
  - Failure: Unbalanced formula (OAV 1-100,000) → oav_balance = 25
  **Evidence:** .omo/evidence/task-2.7-pipeline-improvement.json (oav_balance scores)
  **Commit:** Y | refactor(scoring): rename versatility→oav_balance, use perceptible-only OAVs

- [ ] 2.8. Fix `data_quality` (less aggressive penalty)
  **What to do:** In `engine/pipeline/release_scoring.py:114-121`, reduce the penalty from 3.0 to 1.0 per flagged material. Distinguish between "derived from GC-O" (acceptable for naturals, penalty 0.5) and "estimated/guessed" (truly unreliable, penalty 2.0).
  **Must NOT do:** Do not remove the data quality check entirely.
  **Parallelization:** Wave 2 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/release_scoring.py:114-121` (data_quality calculation)
  **Acceptance criteria:** Formula with 10 naturals (derived ODT) → data_quality = 95 (not 70). Formula with 10 guessed ODTs → data_quality = 80 (not 70).
  **QA scenarios:**
  - Happy: Naturals-heavy formula (10 derived ODTs) → data_quality = 95
  - Failure: Low-quality formula (10 estimated ODTs) → data_quality = 80
  **Evidence:** .omo/evidence/task-2.8-pipeline-improvement.json (data_quality scores)
  **Commit:** Y | fix(scoring): reduce data_quality penalty, distinguish derived vs estimated

### Wave 3: Physics improvements

- [ ] 3.1. Add ethanol to mole fractions in FormulaState
  **What to do:** In `engine/pipeline/formula_state.py:431-506`, add ethanol as an explicit component in the mole fraction calculation. Compute ethanol moles from `batch_volume_ml * 0.789 g/mL / 46.07 g/mol` (assuming 78.9% ethanol density, 46.07 MW). Add to `mole_inputs["ethanol"] = ethanol_moles`. This ensures ethanol (70-80% of product) is included in the mixture composition.
  **Must NOT do:** Do not change the fragrance material mole fractions calculation. Do not assume ethanol has an ODT or OAV (it's a solvent, not a fragrance material).
  **Parallelization:** Wave 3 | Blocked by: None | Blocks: 3.2, 3.3
  **References:** `engine/pipeline/formula_state.py:431-506` (mole fraction calculation), `engine/pipeline/formula_state.py:41` (P_ATM_PA constant)
  **Acceptance criteria:** Formula with 30mL batch, 6mL concentrate → ethanol_moles ≈ 0.41 (30 * 0.789 / 46.07 * 0.8 for 80% ethanol). Fragrance material mole fractions should decrease by ~20-30% (ethanol dilution effect).
  **QA scenarios:**
  - Happy: 30mL EDP (80% ethanol) → ethanol mole fraction ≈ 0.75
  - Failure: If batch_volume_ml is 0, ethanol_moles = 0 (no division by zero)
  **Evidence:** .omo/evidence/task-3.1-pipeline-improvement.json (mole fractions with ethanol)
  **Commit:** Y | feat(physics): include ethanol in mole fraction calculation

- [ ] 3.2. Enable mixture-shifted ODT in pipeline main path
  **What to do:** In `engine/pipeline/formula_state.py:563`, replace `oav_value = oav(vapor_ppm, odt_air_ppm)` with `oav_value = oav(vapor_ppm, mixture_shifted_odt(name, odt_table, conc_table))` where `odt_table` and `conc_table` are built from all materials in the formula. Import `mixture_shifted_odt` from `engine.perception.oav`.
  **Must NOT do:** Do not remove the simple OAV calculation as a fallback (if mixture_shifted_odt returns 0).
  **Parallelization:** Wave 3 | Blocked by: 3.1 (ethanol in mole fractions) | Blocks: None
  **References:** `engine/pipeline/formula_state.py:563` (OAV calculation), `engine/perception/oav.py:64-85` (mixture_shifted_odt implementation)
  **Acceptance criteria:** Formula with 10 materials at OAV 100 each → effective ODT should increase by ~2× (mixture suppression). OAV should decrease accordingly.
  **QA scenarios:**
  - Happy: Complex formula (10 materials) → OAV reduced by 30-50% vs simple OAV
  - Failure: Single-material formula → OAV unchanged (no mixture suppression)
  **Evidence:** .omo/evidence/task-3.2-pipeline-improvement.json (OAV with mixture shift)
  **Commit:** Y | feat(physics): enable mixture-shifted ODT for cross-adaptation suppression

- [ ] 3.3. Add skin temperature correction (32°C default)
  **What to do:** In `engine/pipeline/formula_state.py:44` (DEFAULT_TEMPERATURE_K), change from 305.0 (32°C) to 305.15 (32°C exactly). Add a comment explaining this is skin temperature, not ambient. In `scripts/formula_release_gate.py`, add a `--skin-temperature-k` flag (default 305.15) that overrides the default.
  **Must NOT do:** Do not change the Antoine/CC temperature correction logic.
  **Parallelization:** Wave 3 | Blocked by: 3.1 | Blocks: None
  **References:** `engine/pipeline/formula_state.py:44` (DEFAULT_TEMPERATURE_K), `scripts/formula_release_gate.py:80-120` (CLI argument parsing)
  **Acceptance criteria:** Default pipeline run uses 305.15K. `--skin-temperature-k 310` uses 310K.
  **QA scenarios:**
  - Happy: Default run → temperature_K = 305.15
  - Failure: `--skin-temperature-k 310` → temperature_K = 310.0
  **Evidence:** .omo/evidence/task-3.3-pipeline-improvement.json (temperature config)
  **Commit:** Y | feat(physics): add skin temperature correction with CLI flag

- [ ] 3.4. Fix composite OAV hardcoded γ=0.6
  **What to do:** In `engine/pipeline/natural_absolute_decomposition.py:338`, replace `gamma_estimate: float = 0.6` with a per-constituent γ lookup. For each constituent, check if it exists in `engine.thermo.activity.gamma()` and use the computed γ. If not found, fallback to 0.6.
  **Must NOT do:** Do not remove the gamma_estimate parameter (backward compatibility).
  **Parallelization:** Wave 3 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/natural_absolute_decomposition.py:338` (gamma_estimate parameter), `engine/thermo/activity.py:49-106` (gamma function)
  **Acceptance criteria:** Osmanthus absolute composite OAV should change by ±20% (some constituents have γ > 0.6, some < 0.6).
  **QA scenarios:**
  - Happy: Osmanthus absolute → composite OAV computed with per-constituent γ
  - Failure: Unknown constituent → fallback to gamma_estimate = 0.6
  **Evidence:** .omo/evidence/task-3.4-pipeline-improvement.json (composite OAV with per-constituent γ)
  **Commit:** Y | fix(physics): use per-constituent γ for composite OAV instead of hardcoded 0.6

- [ ] 3.5. Add density data for common materials
  **What to do:** In `data/materials/*.yaml`, add `density_25c_g_ml` values for the top 50 materials by usage frequency. Use PubChem or literature values. For materials without data, keep the default 1.0 but add a comment `# TODO: add density from PubChem`.
  **Must NOT do:** Do not change the DEFAULT_DENSITY_G_ML constant (still 1.0 for missing data).
  **Parallelization:** Wave 3 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/formula_state.py:42` (DEFAULT_DENSITY_G_ML = 1.0), `engine/data_spine/material.py:106` (density_25c_g_ml field)
  **Acceptance criteria:** At least 50 materials have `density_25c_g_ml` values in YAML files. Values range from 0.84 (limonene) to 1.18 (benzyl benzoate).
  **QA scenarios:**
  - Happy: Limonene → density = 0.84 g/mL
  - Failure: Unknown material → density = 1.0 (default)
  **Evidence:** .omo/evidence/task-3.5-pipeline-improvement.yaml (density data coverage)
  **Commit:** Y | data(materials): add density_25c_g_ml for top 50 materials

### Wave 4: Intervention engine

- [ ] 4.1. Add dose-reduction path to formula_recommendations.py
  **What to do:** In `engine/formula_recommendations.py:1089-1100`, add candidate materials for the "safety" axis: `[("hedione", -2.0, "reduce radiance to avoid fatigue"), ("benzyl salicylate", -1.5, "reduce cosmetic weight"), ("iso e super", -3.0, "reduce molecular cocoon")]`. In `engine/pipeline/interventions.py:280-283`, add "DECREASE" and "REMOVE" to the action filter: `{"ADD", "REBALANCE", "INCREASE", "DECREASE", "REMOVE"}`.
  **Must NOT do:** Do not remove the existing ADD/INCREASE/REBALANCE actions.
  **Parallelization:** Wave 4 | Blocked by: 2.1-2.8 (scoring fixes) | Blocks: None
  **References:** `engine/formula_recommendations.py:1089-1100` (AXIS_TO_CANDIDATES), `engine/pipeline/interventions.py:280-283` (swap_candidates filter)
  **Acceptance criteria:** Formula with safety axis score < 40 → recommendation includes DECREASE action for hedione or benzyl salicylate.
  **QA scenarios:**
  - Happy: Overdosed formula (safety score = 30) → DECREASE hedione by 2%
  - Failure: Well-balanced formula (safety score = 80) → no DECREASE recommendations
  **Evidence:** .omo/evidence/task-4.1-pipeline-improvement.json (dose-reduction recommendations)
  **Commit:** Y | feat(interventions): add dose-reduction path for safety/perceptual_clarity axes

- [ ] 4.2. Fix perturbation floor bias for trace materials
  **What to do:** In `engine/pipeline/robustness.py:100`, replace `step = max(5.0, amount * 0.05)` with `step = max(amount * 0.5, amount * 0.05)` (use 50% of amount as floor, not 5µL absolute). This prevents 500% perturbations for 1µL trace materials.
  **Must NOT do:** Do not remove the 5% perturbation logic.
  **Parallelization:** Wave 4 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/robustness.py:100` (perturbation step calculation)
  **Acceptance criteria:** Geosmin 1% at 2µL → step = max(1.0, 0.1) = 1.0µL (50% of 2µL, not 5µL). Iso E Super at 400µL → step = max(200, 20) = 200µL.
  **QA scenarios:**
  - Happy: Trace material (2µL) → perturbation = 1µL (50%)
  - Failure: Large material (400µL) → perturbation = 20µL (5%)
  **Evidence:** .omo/evidence/task-4.2-pipeline-improvement.json (perturbation steps)
  **Commit:** Y | fix(robustness): use proportional perturbation floor instead of absolute 5µL

- [ ] 4.3. Fix single-donor bias in perturbation redistribution
  **What to do:** In `engine/pipeline/robustness.py:141-154`, replace single-donor/single-receiver logic with proportional redistribution. When perturbing material X up by δ, reduce all other materials by `δ * (their_percentage)`. When perturbing X down by δ, increase all other materials proportionally.
  **Must NOT do:** Do not change the perturbation magnitude (still ±5% or 50% floor).
  **Parallelization:** Wave 4 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/robustness.py:141-154` (donor/receiver logic)
  **Acceptance criteria:** Perturb geosmin (0.1% of formula) up by 1µL → all other materials decrease by their percentage share (Iso E Super at 40% loses 0.4µL, not 1µL).
  **QA scenarios:**
  - Happy: Trace material perturbation → largest material loses <10% of δ
  - Failure: If only 2 materials in formula, redistribution still works (50/50 split)
  **Evidence:** .omo/evidence/task-4.3-pipeline-improvement.json (proportional redistribution)
  **Commit:** Y | fix(robustness): use proportional redistribution instead of single-donor bias

- [ ] 4.4. Add temperature perturbation (±5°C)
  **What to do:** In `engine/pipeline/robustness.py`, add a new function `audit_temperature_robustness()` that tests ±5°C from config.temperature_K. For each temperature, run `simulate_formula()` and check if IFRA limits are still respected and brief grammar still matches. Return a list of fragile materials.
  **Must NOT do:** Do not change the existing dosing perturbation logic.
  **Parallelization:** Wave 4 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/robustness.py:99-118` (existing perturbation logic), `engine/pipeline/simulator.py:106-139` (simulate_formula with temperature_K parameter)
  **Acceptance criteria:** Formula with temperature-sensitive material (e.g., citral) → temperature audit WARNs if IFRA limit exceeded at 37°C.
  **QA scenarios:**
  - Happy: Stable formula (±5°C) → temperature audit PASS
  - Failure: Fragile formula (IFRA exceeded at +5°C) → temperature audit WARN with material name
  **Evidence:** .omo/evidence/task-4.4-pipeline-improvement.json (temperature robustness)
  **Commit:** Y | feat(robustness): add temperature perturbation (±5°C) for IFRA safety

- [ ] 4.5. Add heart/drydown robustness testing
  **What to do:** In `engine/pipeline/robustness.py:248-271`, extend the robustness test to include heart (1800s) and drydown (14400s) windows, not just top (300s). For each window, check if family envelope drift exceeds DRIFT_WARN_THRESHOLD.
  **Must NOT do:** Do not remove the top-window test.
  **Parallelization:** Wave 4 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/robustness.py:248-271` (top-window only test), `engine/pipeline/simulator.py:20-26` (DEFAULT_WINDOWS)
  **Acceptance criteria:** Formula with fragile heart (drift > 25% at 1800s) → robustness WARN for heart window.
  **QA scenarios:**
  - Happy: Stable formula (all windows) → robustness PASS
  - Failure: Fragile heart (drift = 30% at 1800s) → robustness WARN for heart window
  **Evidence:** .omo/evidence/task-4.5-pipeline-improvement.json (multi-window robustness)
  **Commit:** Y | feat(robustness): add heart/drydown window robustness testing

### Wave 5: Architecture & output

- [ ] 5.1. Add cost output to analysis
  **What to do:** In `scripts/format_pipeline_analysis.py`, add a new section `build_cost_analysis()` that reads price_data from `release_scoring.py:130-143` and outputs: cost per 30mL bottle, top 5 most expensive materials, cost efficiency score. Insert this section after the gate summary.
  **Must NOT do:** Do not hardcode cost values (use sparse price_data with fallback to "data unavailable").
  **Parallelization:** Wave 5 | Blocked by: 2.1-2.8 (scoring fixes) | Blocks: None
  **References:** `scripts/format_pipeline_analysis.py:40-50` (section ordering), `engine/pipeline/release_scoring.py:130-143` (price_data loading)
  **Acceptance criteria:** Analysis output includes "## Cost Analysis" section with cost per bottle and top 5 materials.
  **QA scenarios:**
  - Happy: Formula with price data → cost per bottle = $12.50
  - Failure: Formula without price data → "Cost data unavailable for 80% of materials"
  **Evidence:** .omo/evidence/task-5.1-pipeline-improvement.txt (cost analysis output)
  **Commit:** Y | feat(analysis): add cost analysis section with per-bottle and per-material breakdown

- [ ] 5.2. Generalize IFRA warnings in analysis output
  **What to do:** In `scripts/format_pipeline_analysis.py:306-315`, replace hardcoded Evernyl/Hedione HC checks with a general IFRA check: iterate over all materials, check `m.get("ifra_limit_pct")`, and warn if `active_pct > ifra_limit_pct * 0.9` (90% of limit).
  **Must NOT do:** Do not remove the Evernyl/Hedione HC special cases (they have additional notes about ODT collisions).
  **Parallelization:** Wave 5 | Blocked by: None | Blocks: None
  **References:** `scripts/format_pipeline_analysis.py:306-315` (hardcoded IFRA checks), `engine/pipeline/formula_state.py:85` (ifra_limit_pct field)
  **Acceptance criteria:** Formula with IBQ at 95% of IFRA limit → WARN "IBQ at 95% of IFRA Cat 4 limit". Formula with all materials < 80% of limit → no IFRA warnings.
  **QA scenarios:**
  - Happy: Formula with restricted material at 95% limit → IFRA WARN
  - Failure: Formula with no restricted materials → no IFRA warnings
  **Evidence:** .omo/evidence/task-5.2-pipeline-improvement.txt (generalized IFRA warnings)
  **Commit:** Y | feat(analysis): generalize IFRA warnings for all restricted materials

- [ ] 5.3. Standardize hedione thresholds across 4 gates
  **What to do:** In `engine/pipeline/gates.py`, consolidate the 4 hedione checks (lines 1320, 1734, 3470, 3462) into a single canonical range: WARN if <10% or >25%, FAIL if >30%. Update `_gate_olfactory_fatigue`, `_gate_literature_compliance`, `_gate_roudnitska_hedione_pct` to use this single range.
  **Must NOT do:** Do not remove any of the 4 gates (they check different aspects beyond just hedione percentage).
  **Parallelization:** Wave 5 | Blocked by: 1.1 (dead gate removal) | Blocks: None
  **References:** `engine/pipeline/gates.py:1320` (olfactory_fatigue), `gates.py:1734` (literature_compliance), `gates.py:3470` (roudnitska_hedione_pct), `gates.py:3462` (roudnitska check)
  **Acceptance criteria:** Formula with hedione at 15% → all 4 gates PASS. Formula with hedione at 28% → all 4 gates WARN (not mixed PASS/WARN).
  **QA scenarios:**
  - Happy: Hedione at 15% → all gates PASS
  - Failure: Hedione at 28% → all gates WARN with consistent message
  **Evidence:** .omo/evidence/task-5.3-pipeline-improvement.json (hedione gate consistency)
  **Commit:** Y | refactor(pipeline): standardize hedione thresholds across 4 gates

- [ ] 5.4. Fix confidence averaging (use min instead of mean)
  **What to do:** In `engine/pipeline/gates.py:4038`, replace `combined = round((confidence["overall_confidence"] + pipeline_confidence) / 2.0, 1)` with `combined = round(min(confidence["overall_confidence"], pipeline_confidence), 1)`. This prevents a weak score from being masked by averaging.
  **Must NOT do:** Do not change the confidence grade thresholds (HIGH/MEDIUM/LOW/VERY_LOW).
  **Parallelization:** Wave 5 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:4038` (confidence averaging), `engine/pipeline/gates.py:4042-4050` (grade thresholds)
  **Acceptance criteria:** Confidence scores (90, 30) → combined = 30 (not 60). Confidence scores (80, 75) → combined = 75.
  **QA scenarios:**
  - Happy: Both scores high (85, 80) → combined = 80
  - Failure: One score low (90, 25) → combined = 25 (not 57.5)
  **Evidence:** .omo/evidence/task-5.4-pipeline-improvement.json (confidence scoring)
  **Commit:** Y | fix(pipeline): use min() for confidence averaging instead of mean()

- [ ] 5.5. Add `_result()` status validation
  **What to do:** In `engine/pipeline/gates.py:193-196`, add validation that `status` is one of "PASS", "WARN", "FAIL". If not, raise `ValueError(f"Invalid gate status: {status}")`.
  **Must NOT do:** Do not change the GateResult dataclass signature.
  **Parallelization:** Wave 5 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:193-196` (_result helper), `engine/pipeline/gates.py:170-180` (GateResult dataclass)
  **Acceptance criteria:** `_result("test", "PASS")` → OK. `_result("test", "WARn")` → ValueError.
  **QA scenarios:**
  - Happy: Valid status ("PASS", "WARN", "FAIL") → no error
  - Failure: Invalid status ("WARn", "pass") → ValueError with message
  **Evidence:** .omo/evidence/task-5.5-pipeline-improvement.json (status validation)
  **Commit:** Y | fix(pipeline): validate gate status strings in _result()

- [ ] 5.6. Fix OAV overdose blocker for ionone-heavy formulas
  **What to do:** In `engine/pipeline/gates.py:1078-1109`, add a hedonic weighting to the OAV overdose check. Materials with high hedonic scores (pleasant even at high OAV) should have a higher threshold: `overdose_threshold = 50_000 if hedonic < 0.5 else 100_000`. Add a comment explaining that ionones naturally have extreme OAV due to ultra-low ODT.
  **Must NOT do:** Do not remove the overdose check entirely (it catches genuine disasters).
  **Parallelization:** Wave 5 | Blocked by: None | Blocks: None
  **References:** `engine/pipeline/gates.py:1078-1109` (OAV overdose blocker), `engine/data_spine/material.py` (hedonic field)
  **Acceptance criteria:** Beta-ionone at OAV 80,000 (hedonic = 0.7) → WARN (not FAIL). Skatole at OAV 60,000 (hedonic = 0.2) → FAIL.
  **QA scenarios:**
  - Happy: Ionone-heavy formula (OAV 80k, hedonic 0.7) → WARN
  - Failure: Unpleasant material (OAV 60k, hedonic 0.2) → FAIL
  **Evidence:** .omo/evidence/task-5.6-pipeline-improvement.json (hedonic-weighted overdose)
  **Commit:** Y | fix(pipeline): add hedonic weighting to OAV overdose blocker

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — verify all 30 todos completed, all acceptance criteria met
- [ ] F2. Code quality review — `python -m pytest tests/test_pipeline_*.py -v` all green, `ruff check engine/pipeline/` clean
- [ ] F3. Real manual QA — run pipeline on 3 test formulas (citrus-heavy, musk-heavy, balanced), verify output changes
- [ ] F4. Scope fidelity — verify no new pipeline scripts created, no backend/frontend changes, no inventory modifications

## Commit strategy
- Atomic commits per todo (30 commits total)
- Commit message format: `<type>(<scope>): <summary>`
- Types: fix (bug fix), feat (new feature), refactor (restructure), data (data files)
- Scopes: pipeline, scoring, physics, interventions, robustness, analysis, materials

## Success criteria
- All 30 todos completed with acceptance criteria met
- All existing tests in `tests/test_pipeline_*.py` remain green
- Pipeline output on test formulas shows:
  - Corrected longevity (not hardcoded 6-8h)
  - Corrected block balance (not substring matching)
  - Reduced gate noise (17 fewer WARNs)
  - Recalibrated scores (impact, tenacity, diffusion, etc.)
  - Mixture-shifted OAV (30-50% reduction vs simple OAV)
  - Ethanol in mole fractions (20-30% dilution effect)
  - Cost analysis section in output
  - Generalized IFRA warnings
- No breaking changes to JSON output schema (deprecation aliases for renamed fields)
