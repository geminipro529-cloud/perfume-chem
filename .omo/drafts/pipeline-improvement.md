---
slug: pipeline-improvement
status: awaiting-approval
intent: unclear
pending-action: write .omo/plans/pipeline-improvement.md
approach: Comprehensive pipeline improvement across 7 components — physics accuracy, gate logic cleanup, scoring recalibration, intervention engine completion, data quality, architecture, and analysis output. Prioritized by impact and effort.
---

# Draft: pipeline-improvement

## Components (topology ledger)

| id | outcome | status | evidence path |
|----|---------|--------|---------------|
| C1 | Physics accuracy — fix UNIFAC stub, ethanol in mole fractions, mixture-shifted ODT, evaporation model | active | engine/thermo/activity.py:66-76, engine/perception/oav.py:64, engine/pipeline/simulator.py:67-79 |
| C2 | Gate logic cleanup — remove 17 dead gates, fix _safe_gate, standardize hedione, fix skeleton threshold | active | engine/pipeline/gates.py:199-211,1258-1332,2579-2620,3096,4337-4682 |
| C3 | Scoring recalibration — fix 8 misnamed/miscalibrated industry_10 scores | active | engine/pipeline/release_scoring.py:83-157 |
| C4 | Intervention engine — add dose-reduction path, fix perturbation bias, add temperature robustness | active | engine/pipeline/robustness.py:100,141-154, engine/formula_recommendations.py:1089-1100 |
| C5 | Data quality — fix sentinel ODTs, add density data, fix farnesene ODT | active | engine/odor_thresholds.py:738,743,446 |
| C6 | Architecture — split gates.py, remove dead oav_intelligence code, add gate phasing | active | engine/pipeline/gates.py (4710 lines), engine/pipeline/oav_intelligence.py (752 lines, 95% dead) |
| C7 | Analysis output — fix hardcoded longevity, block balance, add cost output, generalize IFRA | active | scripts/format_pipeline_analysis.py:272,365-369 |

## Open assumptions (announced defaults)

| assumption | adopted default | rationale | reversible? |
|------------|----------------|-----------|-------------|
| UNIFAC implementation scope | Implement subgroup decomposition for ~130 inventory materials | UNIFAC is the gold standard for γ in fragrance mixtures; Hansen heuristic is a rough approximation | Yes — can keep heuristic as fallback |
| Ethanol in mole fractions | Include ethanol as explicit component in FormulaState | Ethanol is 70-80% of final product; excluding it distorts all mole fractions | Yes — additive change |
| Mixture-shifted ODT | Enable by default in pipeline OAV computation | Already implemented in oav.py:64, just never called; accounts for cross-adaptation suppression | Yes — flag-controlled |
| Gate phasing strategy | 5 phases: preflight → safety → OAV physics → family/literature → future_modules | Short-circuit on FAIL in early phases saves compute; future_modules always last (or removed) | Yes — additive restructuring |
| Scoring axis renaming | Rename misleading axes (lift→top_dominance, character→family_alignment, versatility→oav_balance) | Current names actively mislead users about what's being measured | Yes — output-only change |
| Skeleton OAV threshold | Raise from 0.5 to 1.0 | OAV < 1.0 is sub-threshold (not perceptible); skeleton markers should be functional | Yes — single constant |
| Cost output in analysis | Add cost-per-bottle section using sparse price_data | Hobbyist's #1 practical question; data exists but is never surfaced | Yes — additive |
| Longevity computation | Derive from temporal profile data (scoring.py:1091-1096) instead of hardcoded string | Current "6-8h" is a string literal, never computed from physics | Yes — replacement |

## Findings (cited - path:lines)

### Physics / Headspace (C1)
- **UNIFAC is stubbed**: `engine/thermo/activity.py:66-76` — `pass` instead of implementation; Hansen heuristic is the only active γ method
- **Ethanol excluded from mole fractions**: `engine/pipeline/formula_state.py:431-506` — only fragrance materials counted; ethanol (70-80% of product) absent
- **Mixture-shifted ODT never called**: `engine/perception/oav.py:64-85` — `mixture_shifted_odt()` implements Ferreira 2012-style suppression but pipeline uses raw OAV at `formula_state.py:563`
- **Evaporation is single-exponential**: `engine/pipeline/simulator.py:67-79` — `k = γ × VP / √MW × 2e-5` heuristic; no ethanol co-evaporation, no skin binding, no finite-film model
- **Composite OAV uses hardcoded γ=0.6**: `engine/pipeline/natural_absolute_decomposition.py:338` — no per-constituent activity coefficient
- **Density defaults to 1.0**: `engine/pipeline/formula_state.py:447` — `DEFAULT_DENSITY_G_ML = 1.0` for all materials; real range 0.84-1.18 g/mL
- **Clausius-Clapeyron fallback**: `engine/thermo/antoine.py:36-43` — when Antoine constants missing, uses CC with optional ΔHvap; when ΔHvap also missing, VP is constant (line 42)

### Gate Logic (C2)
- **17 dead future_modules gates**: `engine/pipeline/gates.py:4337-4682` — all return WARN because `future_modules` is never installed (`oav_intelligence.py:16`)
- **`_safe_gate()` swallows all exceptions**: `engine/pipeline/gates.py:199-211` — bare `except Exception` converts crashes to WARN without logging
- **Shelf life temp hardcoded 295K**: `engine/pipeline/gates.py:462` — inconsistent with config default 305K (Bangkok)
- **4 hedione checks, 3 ranges**: `gates.py:1320` (10-25%), `gates.py:1734` (5-20%), `gates.py:3470` (5-25%/30%)
- **Skeleton OAV threshold 0.5**: `gates.py:3096` — sub-threshold; should be 1.0
- **Confidence averaging masks lows**: `gates.py:4038` — (90+30)/2=60 hides the 30
- **30+ skeleton gates run for every formula**: `gates.py:4337-4682` — no family filtering
- **`_result()` doesn't validate status**: `gates.py:193-196` — typo-safe

### Scoring (C3)
- **impact = total OAV, not opening**: `release_scoring.py:83` — `opening_oav = total_oav`
- **tenacity includes heart**: `release_scoring.py:84` — `note in {"base", "heart"}` inflates score
- **diffusion = material count**: `release_scoring.py:89` — `n_percept * 6 + 10`; punishes minimalism
- **lift is semantically inverted**: `release_scoring.py:96` — higher = more top-heavy = worse
- **character = photorealism**: `release_scoring.py:151` — misnamed; not family alignment
- **temporal_coherence penalizes linear**: `release_scoring.py:99-112` — low delta → division by 0.01 → score drops to 0
- **versatility = OAV range**: `release_scoring.py:123-127` — penalizes structural trace materials
- **cost_efficiency always 50 or 100**: `release_scoring.py:129-143` — sparse data or capped
- **data_quality too aggressive**: `release_scoring.py:114-121` — 34 materials × 3 = 0%

### Intervention Engine (C4)
- **No dose-reduction path**: `engine/formula_recommendations.py:1089-1100` — only ADD/INCREASE/REBALANCE; `safety` axis has empty candidates
- **Perturbation floor 5µL**: `engine/pipeline/robustness.py:100` — `max(5.0, amount * 0.05)` = 500% for 1µL trace materials
- **Single-donor bias**: `engine/pipeline/robustness.py:141-154` — largest material always absorbs all perturbation cost
- **Only top-window tested**: `engine/pipeline/robustness.py:248-271` — no heart/drydown robustness
- **No temperature perturbation**: robustness.py — only dosing ±5%, no ±5°C test
- **3 empty recommendation axes**: `formula_recommendations.py:1089-1100` — perceptual_clarity, luxury, safety

### Data Quality (C5)
- **ODT sentinel 0.0**: `engine/odor_thresholds.py:738,743` — "amber core" and "amber core accord" have odt_air=0.0
- **Farnesene ODT 100.0**: `engine/odor_thresholds.py:446` — suspiciously high, likely placeholder
- **Density data sparse**: `engine/data_spine/material.py:106` — `density_25c_g_ml: float | None = None` for most materials
- **Composite OAV γ=0.6 hardcoded**: `engine/pipeline/natural_absolute_decomposition.py:338`

### Architecture (C6)
- **gates.py is 4710 lines**: monolithic, no module split
- **oav_intelligence.py 95% dead**: 752 lines, `_FUTURE_MODULES_AVAILABLE = False` at line 16; only `_minimal_intelligence_result()` executes
- **No gate phasing**: 80+ `_safe_gate()` calls in flat sequence
- **Formula name parsing not shared**: `scripts/formula_release_gate.py` handles .md parsing; `gate_formula()` expects pre-parsed dict

### Analysis Output (C7)
- **"Est. skin life: 6-8h" hardcoded**: `scripts/format_pipeline_analysis.py:272` — string literal, never computed
- **Block balance substring matching**: `scripts/format_pipeline_analysis.py:365-369` — hardcoded citrus/base names; everything else = "floral"
- **No cost output**: cost data exists in `release_scoring.py:130-143` but never passed to analysis
- **Hardcoded IFRA checks**: `scripts/format_pipeline_analysis.py:306-315` — only Evernyl and Hedione HC
- **Perfumer section duplicates earlier sections**: lines 185-317 largely repeat headspace table, note distribution, temporal data

## Decisions (with rationale)

1. **Prioritize by user-visible impact**: C7 (analysis output) and C3 (scoring) are most visible to the perfumer. C1 (physics) is most scientifically important. C2 (gate cleanup) reduces noise. C4-C6 are infrastructure.
2. **Phase the work**: Wave 1 = quick wins (C7 fixes, C2 dead gate removal). Wave 2 = scoring recalibration (C3). Wave 3 = physics improvements (C1). Wave 4 = intervention engine (C4). Wave 5 = architecture (C6).
3. **Keep backward compatibility**: All scoring changes should preserve the JSON output schema; rename fields with deprecation aliases.
4. **Test-first for physics changes**: Any change to formula_state.py or simulator.py needs regression tests pinning current behavior first.

## Scope IN

- All 7 components (C1-C7)
- Tests for every behavior change
- Updated AGENTS.md documentation for new gate behavior

## Scope OUT (Must NOT have)

- New pipeline scripts (RULE 2)
- Changes to backend/ FastAPI app (separate concern)
- Frontend changes
- New formula family archetypes (separate concern)
- Changes to inventory.txt or material YAML files (data entry, not pipeline logic)

### External Best Practices (Librarian Research)
- **HANNA** (Chemical Science, 2024): ML-based γ prediction, open-source, SMILES-only input, outperforms UNIFAC. Trained on 317k data points from DDB. Gibbs-Duhem hard-constrained.
- **UNIFAC-Dortmund**: 95.4% agreement with experimental odor character across 65 fragrance mixtures (Teixeira et al. 2011). mod. UNIFAC 2.0 (2025) fills all gaps via matrix completion.
- **Competitive binding model** (Singh et al. 2019): Replaces simple OAV with receptor competition. Predicts OR responses to 12-component mixtures within 15% of experimental data. Explains overshadowing, suppression, masking.
- **Stevens' Power Law** (Teixeira 2010): `I = k × OAV^n` (n=0.2-0.6 family-specific). Already implemented in `engine/perception/oav.py:51-55` but NOT used in pipeline main path.
- **Two-stage evaporation** (Teixeira 2009-2010): Finite-film diffusion with UNIFAC VLE. Stage 1 (0-5min): ethanol-dominated rapid release. Stage 2 (5min+): diffusion-controlled fragrance release.
- **Skin temperature**: 32°C (not 25°C) for skin applications. 7°C rise = 50-100% VP increase (Almeida 2021, Franz cell study 2025).
- **ALETHEIA API**: Free tier (500 queries/day, no API key). 1,886 compounds, 2,325 fragrance ingredients. IARC, EPA, EFSA, Prop 65 classifications.
- **OpenMix** (Apache 2.0): Python framework for computational formulation science. Ingredient resolver (INCI→SMILES), physics observation engine (273 rules), MCP server.
- **Pyrfume**: Python package with 6,000+ molecule-percept pairs. ODT data enrichment source.
- **Livermore & Laing misinterpretation**: The "3-4 component limit" is about IDENTIFICATION, not PERCEPTION. Pipeline's `_gate_livermore_laing` warns at >4 perceptible channels, which misinterprets the science.
- **HSP is NOT state-of-the-art**: Comparative study (I&EC Research 2019) shows HSP significantly worse than MOSCED (16.2% ARD), UNIFAC (24-32%), or COSMO-RS for γ prediction.
- **POMMix** (ICLR 2025): SOTA for mixture similarity prediction using graph attention networks.
- **VIANA** (2026): GCN + POM embeddings + Hill's law. R²=0.996 for intensity prediction.

## Open questions

- None — all resolved to best-practice defaults per UNCLEAR intent routing.

## Approval gate
status: awaiting-approval
<!-- Exploration complete from 4 research streams. Librarian (external best practices) still running — will fold into plan if results arrive before approval. -->
