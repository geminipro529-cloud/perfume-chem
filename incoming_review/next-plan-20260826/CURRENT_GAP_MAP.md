# Perfume-Chem Post-Publication Gap Map — 2026-08-26

## Exact publication baseline

- GitHub branch: `codex/complex-perfumery-publish`.
- Commit: `e545237f5d41b063d7fe920401671e3603b71794`.
- The remote branch and local commit were verified equal after push.
- The focused complexity/SolForge shard passed 637 tests.
- Gate Foundation V2 passed 163 tests.
- Vertical Slice V2 passed 220 root tests and 7 backend tests.
- The quick pre-push verifier passed every selected check; full completion and release readiness were not evaluated by the quick run.
- All formula, inventory, compounding, physical, sensory, hedonic, safety, purchase, publication, and release authority remains false.

## Frozen runtime and benchmark state

- `configs/complexity/complexity_module_registry_v5.json` admits only `architectural-delta-engine`.
- Architectural Delta achieved 5/6 wins against plain Sol 5.6 xhigh and 5/6 against the length-matched placebo, median paired gain 20 against each, and zero critical errors.
- `temporal-sensory-ledger` is `RETIRED_BENCHMARK_UNDERPERFORMER`; it tied plain Sol on all three screen cases and won one case against placebo.
- `hedonic-preference-learner` is `RETIRED_BENCHMARK_UNDERPERFORMER`; it tied plain Sol on two screen cases and won only the order-confounding trap.
- Perceptual Topology and Wood Depth remain nonruntime future candidates pending fresh blinded evidence.
- Admission still requires at least 2/3 screen wins against both controls with zero critical regressions, followed by at least 4/6 total wins, median paired gain at least five against both controls, and zero critical errors.

## Current time-resolved OAV surfaces

- `engine/pipeline/oav_evidence.py` defines row-level `OAVMaterialEvidenceInput`, `OAVEvidenceRequest`, `OAVMaterialEvidenceResult`, `OAVEvidenceResult`, and `evaluate_oav_evidence`.
- The existing request binds one formula hash, one dose-receipt hash, one measurement context, and material rows. It does not expose a canonical `(sample, material, timepoint, endpoint)` evidence-cell identity.
- Existing row states are `STRICT_MEASURED`, `MODELED_SCREEN`, `PARTIAL`, `ABSTAINED`, and `INVALID`.
- Existing results prohibit odor-contribution, balance, diffusion, liking, beauty, synergy, similarity, and release claims.
- `engine/fuckups/pre_mix_guard.py` separately enforces active-dose continuity and accepts untyped parent/child time-series mappings for temporal OAV anomaly screening.
- The pre-mix guard correctly makes active-dose continuity hard authority and modeled temporal OAV screening advisory only.
- `engine/sensory/ledger.py` already has exact temporal sensory cells, protocol scope, duplicate/missing-cell handling, assessor reliability, order balance, transitions, and within-sniff qualification.
- Predicted OAV time series and observed sensory time series must remain separate evidence classes.

## Downloads OAV time-dose candidate

- `OAV_TIME_DOSE_ERROR_SENTINEL_LITERATURE_BASIS_v1.md` has SHA-256 `1094ef77c35b955ca0b6e13bc4d79981e6c78f2fcbaccaf6d34b5a175fa2e7c9`.
- It separates deterministic active-dose integrity from static OAV, relative threshold-cancelling headspace comparisons, and uncertainty-bounded temporal models.
- It proposes explicit model tiers from deterministic exposure through measured time-resolved headspace, five required times, P05/P50/P95 concentration and OAV, threshold-method compatibility, human-variability flags, natural/preblend restrictions, and adversarial regressions.
- Current code already covers active-dose continuity, stock rebase, modeled/measured separation, OAV claim firewalls, natural-composite handling, and row-level evidence states.
- Potential nonredundant gaps are typed temporal evidence cells, uncertainty intervals, authority tiers by timepoint, threshold-cancellation conditions, and exact provenance across time.
- The candidate document is not code authority. Every scientific source and every proposed threshold must be independently verified before implementation.

## Current hedonic and preference surfaces

- `engine/preference.py` defines criterion-scoped pairwise comparisons, Davidson-capable outcomes, deterministic assessor-cluster bootstrap, held-out baseline checks, heterogeneity/order diagnostics, and deterministic next-pair selection.
- `engine/hedonic_evidence.py` binds preference fits to exact formula/build, sample, protocol, criterion, assessor, repeat, time, schedule, bootstrap, and validation receipts.
- `engine/optimizer/scoring.py` blocks the active scoring route when a hedonic weight is nonzero and reports liking as `NOT_TESTED` without an exact-scope receipt.
- `engine/hedonic_model.py` remains importable only for legacy replay, and several historical top-level analysis scripts still print scalar hedonic or pleasantness claims from it.
- `tests/test_legacy_hedonic_runtime_isolation.py` verifies that active scoring does not call the legacy model.
- The remaining scientific weakness is not absence of a gate; it is lack of sufficient real, blinded, criterion-specific, held-out sensory observations and an augmentation that adds useful calculations beyond what plain Sol already states.

## Candidate reference work from Downloads

- `FLORAL_COVERAGE_FOUNDATION_v2.zip`: 9 families, 12-slot spine, 27 branches, 294 role records, 20 primary-source records, 108 screen-reuse records, 12 confusion pairs, and 40 package tests; zero physical results, zero similarity passes, and no Phase G authority. Reference/semantic merge only.
- `COMPLEX_PERFUMERY_OPUS_V_COMPLEXITY_SYSTEM_V1R2_20260811.zip`: 69 tests and 36 validation checks; closes fail-open defects but changes no formula or empirical state. Regression provenance only.
- `Woody_Amber_Musk_Extreme_Research_Bundle_V2.zip`: 34-source register, 19 profiles, and 37 materials; obsolete Inventory V3 and physical status `NOT RUN`. Source-by-source literature triage only.
- `Top_Complexity_Microevent_Bundle_v2.zip`: 42 formulas and a mandatory count of at least 50 identities; scientific state `NOT RUN`, appeal `NOT TESTED`, target authority `NONE`. Reject as count trap.
- `Perfumery_Formula_Control_Ensemble_v2_1.md` conflicts with current Ambrettolide authority by calling Ambrettolide 10% DPG owned. Conflict-preserved provenance only.

## Planning constraints

- Sol Ultra owns architecture, scientific interpretation, security, scope, benchmark design, and final acceptance.
- DeepLuna may perform only bounded file inventories, requirement extraction, citation deduplication, and checklist assembly.
- Do not create another parallel OAV, temporal, preference, floral, wood, musk, or amber runtime.
- Extend current exact contracts or add a compatibility-preserving evidence layer.
- Keep TARGET / IDEAL separate from CURRENT-INVENTORY.
- Ingredient count, formula frequency, supplier prose, price, prestige, darkness, modeled OAV, and predicted volatility cannot establish richness, depth, liking, or beauty.
- Missing, duplicate, order-confounded, unscoped, or incompatible evidence must fail closed.
- No module is retested externally until provider-free recovery, falsification, hash, and authority tests pass.
- Failed benchmark candidates remain runtime-unreachable provenance tombstones.

## Required plan output

The next plan must prioritize the smallest foundation that unlocks trustworthy temporal and hedonic work. It must identify exact files and tests, use TDD, define stop/go gates, preserve backward compatibility, include a fresh three-arm blinded benchmark only after provider-free validation, and defer floral/wood/Opus/Amouage runtime admission until the evidence foundation is demonstrably better than both controls.
