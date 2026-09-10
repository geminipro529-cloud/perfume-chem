# Step 2 completion record — numeric character contract and receipt binding

Provenance: drafted by lane `D:\chatbots\.lanes2-20260910\20-step2-record` (detached worktree at
`cc2693eb`), reviewed and committed with a subsequent-commits appendix. Commit sizes and hashes
below were taken from the committed bytes of this repository.

---
# Step 2 completion record — Repair the shared data and software contracts

Draft for `docs/governance/step2_numeric_character_and_receipt_20260910.md`.

Scope and identity (verified from committed bytes at `cc2693eb`):

- Repository: `D:\chatbots\perfume-chem-integration-20260909`, branch `codex/integration-20260909`.
- Step 2 base: `601d203cbd5445e8a84a257bd205a812a34d30ee` ("Integrate post-cutoff inventory and identity authority").
- Commit A: `8916c30bda979a74b60d3006aaf3200ceaf10bf2` — "Add explicit numeric character evidence contract" (Codex <codex@local>, 2026-09-10 23:50:37 +07:00).
- Commit B: `cc2693eb7b76ddac9b0c208c0507b13b7be4ba7f` — "Restore default dose-receipt binding and rebuild stale stock fixtures" (Codex <codex@local>, 2026-09-10 23:50:57 +07:00).
- Combined size: 22 distinct files, +688 / −186 lines (A: 16 files, +522 / −153; B: 6 files, +166 / −33).
- Numbers stated below are from bounded runs and committed bytes; anything not re-verified is marked UNKNOWN.

## 1. Commit A — explicit numeric character evidence contract (`8916c30b`)

### 1.1 Contract (`engine/ingredient_intelligence.py`)

- New `CharacterEvidenceStatus` enum: `AVAILABLE`, `PROSE_ONLY`, `MISSING`, `INVALID_NUMERIC`. New `NumericCharacterUnavailable(ValueError)`.
- `MaterialProfile` now validates character evidence at construction:
  - `character` is a compatibility input only. After validation it is either the same numeric mapping as `numeric_character` or `None`; prose is never treated as data.
  - Prose is preserved in `character_description` (a prose string passed as `character` is moved there).
  - Accepted dimensions are the 13-dimension contract only; keys outside it are recorded in `character_excluded` and never consumed as evidence.
  - Fail-closed rules: non-mapping input, empty mapping, booleans, non-real numbers, non-finite values, and values outside 0..10 yield `INVALID_NUMERIC` with `numeric_character = None`. A materially empty mapping also yields `INVALID_NUMERIC` and names the excluded keys. No numeric and no prose yields `MISSING`; prose only yields `PROSE_ONLY`.
  - Legitimate zeroes and sparse mappings are preserved as `AVAILABLE`.
- New `require_numeric_character()` raises `NumericCharacterUnavailable` with material name, status, and reason. `dimension_vector()`, `dominant_character()`, and `character_tags()` now call it, so they raise instead of zero-filling or returning "neutral".
- New `find_similar_with_evidence()` returns `CharacterSimilarityResult(ranked, unavailable, source_status)`; `find_similar()` delegates to it. A prose-only source returns empty rankings and reports the status rather than ranking unusable candidates.
- `suggest_replacement()` returns "numeric character evidence unavailable — browse inventory by note" when the missing material has no numeric vector, and otherwise uses an explicit L2 distance score (threshold 7.0).

### 1.2 Consumers updated to suppress character-derived claims

| File | Change |
|---|---|
| `engine/fingerprint.py` | `MaterialFingerprint.character_status`; `FormulaFingerprint.character_coverage_fraction` and `character_missing_materials`; `character_radar()` returns `None` below full coverage; `dominant_character()` returns `None`; `material_similarity()` / `formula_similarity()` return `None` on incomplete evidence; `find_similar_materials()` skips non-`AVAILABLE` candidates. |
| `engine/chemical_life_graph.py` | `character_vector`, `weight_diagnosis`, `health_score` are now nullable; graph carries coverage fraction and missing-material list from the fingerprint; summary prints `UNKNOWN (incomplete numeric character evidence)`; dimension-gap detection is skipped when character is unavailable. |
| `engine/temporal_graph.py` | `MaterialTemporal.character` nullable; unknown materials no longer receive an invented `{"warmth": 3, "sweetness": 2}` profile; character-evolution curves skip uncovered materials and record `character_coverage_fraction` + missing list; ODT estimation applies potency factor 1.0 (no fabricated intensity) when character is missing. |
| `engine/optimizer/scoring.py` | Guards in the character-weighted helpers (≈2266, 2512) and in the "strong character" saturation term; dominant-dimension counting only with numeric evidence. See §4.1: the radar itself is still coverage-blind. |
| `engine/optimizer/models.py` | `material_roudnitska_roles()` returns an empty set when numeric character is unavailable. |
| `engine/formula_analyzer.py` | `suggest_changes()` skips materials without numeric character; life-graph summary prints `UNKNOWN` for a missing health score; `run_analysis()` prints `UNK`. |
| `engine/aromachemical_expansion.py` | Coverage/depth/scoring guards; no character-coverage credit without candidate evidence; closest-owned comparison restricted to numerically comparable profiles. |
| `engine/synergy_graph.py` | Character-only deductions skipped without numeric evidence; character totals return `{}` when any ingredient lacks evidence. |
| `engine/perspectives.py` | Ellena and Laudamiel character terms skipped without numeric evidence. |
| `engine/chemical_data_validator.py` | Odor description falls back to prose; dominant character only when numeric evidence exists. |
| `engine/ingredient_catalog.py` | Properties now carry `character_evidence_status` and `character_description`; `dominant_character` / `character_tags` are `None` when unavailable. |
| `scripts/scan_inventory.py` | Prints `character=<STATUS>` instead of an empty vector. |
| `scripts/record_verification_outcome.py`, `scripts/verify_formula_workflow.py` | Print `UNKNOWN (incomplete numeric character evidence)` instead of formatting a missing score. |

### 1.3 Test added

`tests/test_numeric_character_contract.py` (new, 89 lines, 6 test functions / 12 collected cases): prose preserved without becoming a numeric vector; sparse mapping and legitimate zero; invalid values fail closed (7 parametrized cases incl. bool, NaN, inf, out-of-range, non-dimension key, non-mapping); missing numeric evidence distinct from unknown identity; similarity reports unavailable candidates and never ranks a prose source; alias cache preserves canonical evidence status.

## 2. Commit B — default dose-receipt binding and rebuilt stock fixtures (`cc2693eb`)

### 2.1 Gate behavior (`engine/pipeline/gates.py`)

`gate_formula()` previously built a dose receipt but only bound `state.dose_receipt_sha256` / `status` and forwarded the receipt to `run_release_preflight()` when `deep_plane_diagnostics_enabled` was set. After the change:

- the receipt is built by default and bound into the state whenever it is built;
- the receipt is always forwarded to `run_release_preflight(...)`;
- `ValueError` from an unbuildable receipt still falls through to the existing fail-closed preflight, except when deep-plane diagnostics are enabled, where it is re-raised (unchanged strictness).

### 2.2 Fixtures and pinned expectations rebuilt against the current inventory authority

| File | Change |
|---|---|
| `tests/test_aromachemical_expansion.py` | Inventory size is parsed from the public authority instead of the hard-coded 210; owned identities are excluded from recommendations; depleted stock appears only via explicit replenishment and the two modes are disjoint; new deterministic fixture test proves the count is exact. |
| `tests/test_c3_model_interface.py` | C3 export-equality assertion extended with the supported lifecycle symbols (`ModelLifecycleCard`, `ModelLifecycleState`, `ModelDriftState`, `ModelDriftObservation`, `ModelDriftAssessment`, `assess_model_drift`). |
| `tests/test_pipeline_part5.py` | Trial fougère rebuilt on executable stock: Cedrat FCF → Bergamot FCF oil Sicilian, Evernyl → Patchouli EO, Coumarin 30% → 10%; markdown fixture updated to match. |
| `tests/test_pipeline_robustness.py` | Stock-valid variant for the advisory gate case; the Evernyl IFRA perturbation case keeps its original material (it does not run the release gate); dilution map corrected (10% Coumarin on the stock-valid path). |
| `tests/test_pipeline_scenario_matrix.py` | Prada control expectations rebuilt to the current exact issue sets (`inventory_gap`, `stock_fraction_mismatch`, `stock_carrier_mismatch`, `inventory_stock_metadata_incomplete`); unresolved-natural matrix pins 24 naturals missing composite evidence and 4 opaque preblends, with `status == FAIL_CLOSED_GAPS` and `release_authority is False`. |

## 3. Evidence — commands actually run

Environment: interpreter `D:\chatbots\perfume-chem-integration-20260909\.venv\Scripts\python.exe` (Python 3.11.15, pytest 9.1.1), working directory `D:\chatbots\.lanes2-20260910\20-step2-record` (lane worktree, detached at `cc2693eb`). `OPENAI_API_KEY=test-key`, `SECRET_KEY=test-secret-key-for-ci`. Only focused runs; the full suite and backend pytest were not run (out of bounds for this lane), and `project-verify --quick` was left to the dedicated lane.

| # | Command (args abbreviated) | Byte state | Result | Log sha256 |
|---|---|---|---|---|
| 1 | `-m pytest tests/test_numeric_character_contract.py -q` | as checked out | **12 passed** in 1.12s | `ab264d7b…` |
| 2 | `-m pytest tests/test_aromachemical_expansion.py tests/test_pipeline_part5.py tests/test_pipeline_robustness.py tests/test_pipeline_scenario_matrix.py tests/test_c3_model_interface.py -q` | as checked out (CRLF receipts) | **141 passed, 11 failed** — all 11 fail closed with `InventoryAuthorityError: 2026-09-10 successor source binding drift` (`engine/inventory_parser.py:1879`) | `8a2c0a2b…` |
| 3 | same five files as #2 | two receipt JSONs temporarily materialized as their committed LF bytes | **152 passed** in 17.34s | `f6f70cad…` |
| 4 | `-m pytest tests/test_optimizer_determinism.py tests/test_optimizer_thermodynamic_unification.py tests/test_gate_aware_optimizer.py tests/test_release_scoring_contract.py tests/test_temporal_observations.py tests/test_formulation_intelligence_mixture_temporal.py tests/test_kb_migration.py tests/test_verify_formula_workflow_parser.py -q` | LF receipts | **97 passed, 1 failed** (`test_kb_migration::test_every_inventory_material_exists`: `Guaiacwood EO` not in DB) | `61aa96b9…` |
| 5 | `-m pytest tests/test_c6_dynamic_release.py tests/test_c8_headspace_oav.py tests/test_musk_design.py tests/test_inventory_material_additions.py -q` | LF receipts | **201 passed, 1 failed** (`Jasmine Sambac Absolute` composite metadata `resolution` is `normalized_identity`, expected `literature_proxy`) | `effc1c2c…` |
| 6 | `-m pytest tests/test_pipeline_preflight.py tests/test_pipeline_gates.py tests/test_pre_mix_guard.py tests/test_inventory_stock_clarifications_2026_09_10.py tests/test_inventory_ahsee_stock_2026_09_08.py tests/test_inventory_neroli_stock_2026_09_06.py tests/test_inventory_orris_stock_2026_09_05.py tests/test_inventory_stock_model.py -q` | LF receipts | **123 passed, 1 failed** (`test_new_head_rejects_live_text_drift` expects message `live inventory text`, which exists nowhere in current engine code) | `44331c9d…` |

Combined: 588 collected cases across the six commands (12 + 152 + 98 + 202 + 124), excluding the repeat of the same 152 cases under CRLF bytes in run 2.

The three single failures are inherited, not introduced by Step 2: `git diff 601d203c cc2693eb` is empty for `engine/inventory_parser.py`, `data/materials`, `inventory.txt`, `tests/test_kb_migration.py`, `tests/test_inventory_material_additions.py`, and `tests/test_inventory_neroli_stock_2026_09_06.py`, so none of those code, data, or expectation paths changed between the Step 2 base and `cc2693eb`. The acceptance record already lists "missing Guaiacwood migration coverage" and prose/historical mismatches as holds.

Lane restoration: after the runs, both receipt files were restored to their as-checked-out bytes (`80545ea8…`, `a2a1fdc9…`) via `git checkout-index -f`, and `git status --porcelain` reports only `?? _lane_out/`. No commit, merge, push, or reset was used; the only worktree writes were the temporary byte materialization in run 3 and the index-based restoration, both verified by hash.

### 3.1 Findings from verification (for the parent; not Step 2 changes)

- **F1 — raw-hash receipt pins are line-ending fragile.** `engine/inventory_parser.py` binds `_file_sha256()` (raw bytes) for the two 2026-09-10 receipts at lines ≈1875/1877, while the recorded pin equals the LF content. A fresh `git checkout` on this machine (`core.autocrlf=true`) materializes CRLF, so 11 fixture tests fail closed with a misleading "successor source binding drift" until the bytes are the committed LF form. The main integration checkout currently holds LF bytes for these files (consistent with tooling rewriting them); any new worktree, CI checkout, or fresh clone can hit F1. Normalized hashing (already used for `inventory.txt` and the overlay at ≈1866/1867) would be portable.
- **F2 — verification runs rewrite tracked governance JSONs.** A focused run rewrote 11 tracked files under `data/governance/` with LF endings as a side effect (all 11 share one write time, 2026-09-11 00:29:23; e.g. `inventory_worktree_sync_20260830.json`, `complexity_native_module_admission_20260822.json`). Content is identical after EOL normalization, but the worktree status becomes dirty; the exact writer was not isolated. Probably the same mechanism that left the main checkout's files in LF form. Restored here; verification should run in a disposable worktree or be followed by an explicit restore step.

## 4. What remains open

### 4.1 Coverage-aware character radar (not addressed by Step 2)

`FormulaScorer.formula_character_radar()` (`engine/optimizer/scoring.py:2512`) still excludes non-numeric profiles and then divides by the covered mass only (lines 2520–2531), so a formula with missing character evidence gets a plausible-looking full radar. Step 2 only stopped non-numeric profiles from contributing; it did not gate the aggregate.

Consumers still exposed (line numbers at `cc2693eb`):

- `engine/optimizer/scoring.py`: internal call sites 1123, 1283, 1344, 1566; `_radar` export 3192; additional read at 2808.
- `engine/formula_analyzer.py`: radar render 871; derived axes `balance` / `radiance` / `character_balance` 1204–1216; star ratings 1225 via `engine/formula_rating.py` (`compute_star_ratings`, `rate_wearability`, `rate_versatility`, `rate_originality`, all reading `character_radar` dicts).

### 4.2 Evidence successors

The required current-state successors (C0 physical-model binding, C5 current-inventory material panel, D0 claim matrix on quarantined formula bytes, backend corpus baseline) remain holds per the acceptance record ("Historical C0/C5/D0, panel, corpus, and formula source/receipt mismatches"). What exists today, replayability, and the smallest next action per successor are UNKNOWN in this record (separate analysis owns that). Historical receipts must remain byte-for-byte; nothing here repeals that.

### 4.3 OAV / composite data holds

- OAV coverage remains **84.553%** (208 supported / 246 materials) with `release_authority: false`, below the unchanged `>85%` criterion (`docs/governance/integration_closure_review_20260909.md:70`; acceptance-record limitation).
- The audit categories pinned by the passing scenario-matrix test at `cc2693eb`: **24** naturals missing composite evidence; **4** opaque preblends without disclosed composition; audit status `FAIL_CLOSED_GAPS`. The `Peppermint EO` / `Peppermint Essential Oil` duplicate suspicion remains unresolved (both appear in the pin).
- Identity counts differ across records (7 "unresolved identities" in the closure review vs 11 "unknown_material_identities" in the current plan's live audit); whether those are the same category is UNKNOWN and reconciliation is outstanding.
- Guaiacwood: `inventory.txt:200` carries "Guaiacwood EO (exactly 1/3 w/w in ethanol + DEP …)", but no `data/**/*.yaml` contains Guaiacwood and `test_kb_migration::test_every_inventory_material_exists` fails with `Guaiacwood EO` missing from the KB database. This matches the recorded hold "missing Guaiacwood database migration coverage".

### 4.4 Other inherited holds (recorded; not re-measured here)

None of the following were re-measured in this lane and are UNKNOWN as current values: full-verifier group status (12 pass / 8 fail / 2 skipped at acceptance time), backend/Docker groups, formula artifact states (456 `NONE`, 14 `QUARANTINED`, 7 `STALE`, 49 `UNBOUND_LEGACY`), workbench/security gaps, and protected-evidence/workbench blockers.

## 5. Authority

**No release authority is granted by this record.** The consolidation acceptance remains `release_ready: false`, `production_activation: false`, `pushed: false`. The two commits are local-only repairs of shared contracts; they unlock no release, no scientific promotion, no physical compounding, no purchase authority, and no database migration. The full verifier remains FAIL; this record does not supersede it and does not claim a green repository.

## Draft provenance (lane 20; strip or trim before committing)

- Lane: `D:\chatbots\.lanes2-20260910\20-step2-record` (full detached worktree of the integration repo at `cc2693eb`), claimed with `_lane_out\CLAIMED`.
- Raw evidence in `_lane_out\evidence\`: `diff_8916c30b.patch` (`6a91870c…`), `diff_cc2693eb.patch` (`88c39dbe…`), and the six pytest logs listed in §3.
- Verification was bounded by design: no full suite, no backend pytest, no repository-wide verifier, no external providers.

## What this means for the approach

Step 2 fixed a real default-path breakage (every default release-gate run needing a receipt it never received) and made a whole class of character claims fail closed instead of being silently fabricated. That is worth having. But the evidence state of the repository is unchanged in the places that matter most: the character radar still renormalizes over covered mass, so style/balance/star claims built on it remain unsupported for any formula with prose-only materials; the OAV/composite and identity holds are untouched; and the successor work is still ahead. The most valuable next step is therefore not more fixture churn but the coverage-aware radar plus the identity/OAV reconciliation, because those directly govern whether the tool's character claims can be trusted. Two operational cautions from the verification: fix the raw-hash receipt pinning (F1) so fresh checkouts and CI do not fail closed spuriously, and run verification in disposable worktrees (F2) so test side effects do not dirty tracked governance data. As a record, this document is honest only if §4 stays attached to it — Step 2 is done, the Step 2 *promise* is not.

## Subsequent commits (appendix added during harvest)

These landed after the record was drafted and are part of the same Step 2 workstream:

- `7408a9e7` — "Suppress character-similarity and radar claims without numeric evidence": synergy
  fingerprint edges require `AVAILABLE` character evidence; the verification workflow prints
  explicit unavailable lines instead of dropping the radar and weight-diagnosis sections.
- `f19adc5d` — "Treat unavailable character evidence as unknown in gap detection": gap filler
  suggestions carry `gap_family_basis`; `scan_inventory.py` survives a cp874 console.
- `498724c5` — "Pin LF checkout for raw-byte-hashed governance receipts": thirteen governance JSONs
  declare `text eol=lf`, so fresh worktrees no longer fail the raw-byte inventory-authority pins.
- `240494d9` — "Keep simulation provenance consistent with the bound dose receipt": frames bind
  provenance whenever the state carries a receipt, so the exact OAV replay reproduces; the live OAV
  audit test asserts the measured contract and the below-threshold hold rather than a passing gate.