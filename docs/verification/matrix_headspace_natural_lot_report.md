# Build C11 Matrix, Headspace, and Natural-Lot Evidence Report

Status: `DRAFT_PENDING_FINAL_DEEPLUNA_AUDIT_COMMITTED_BLOB_MANIFEST_AND_DETACHED_REPLAY`

This is a draft C11 aggregate evidence packet. It records software-contract verification and fail-closed scientific boundaries. It does not authorize Build D, production formulation, a database migration, or an empirical perfume-performance claim.

## Authoritative state

- Source commit: `f8d8c6836643cf8bd7693d1e6672daded9629c69`
- Branch: `codex/add-inventory-materials`
- Build C exit gate: `false`
- Build D authorized: `false`
- Real instrument observations: `0`
- Real natural-lot profiles: `0`
- Historical 30k/35/97.76 replay: `BLOCKED_MISSING_REPRODUCIBLE_ARTIFACT_BUNDLE`

## Requirement crosswalk

| ID | Requirement | Result | Authority boundary |
|---|---|---|---|
| C11-REQ-001 | property range and condition selection | PASS | SOFTWARE_CONTRACT_ONLY |
| C11-REQ-002 | vapor-pressure equation validity range | PASS | REPRESENTATION_AND_SELECTION_ONLY_NO_EVALUATOR |
| C11-REQ-003 | trusted UNIFAC reference or abstention | PASS_ABSTENTION | UNIFAC_UNAVAILABLE |
| C11-REQ-004 | group-decomposition coverage | PASS_ABSTENTION | DATA_ONLY_STUB_NO_MOLECULE_ASSIGNMENT_OR_GAMMA_SOLVER |
| C11-REQ-005 | COSMO-RS import integrity | PASS_ABSTENTION | NO_EXECUTABLE_OR_IMPORT_PRESENT |
| C11-REQ-006 | explicit fallback | PASS | FAIL_CLOSED_NO_SILENT_FALLBACK |
| C11-REQ-007 | ideal baseline | PASS_THEORETICAL_BASELINE_ONLY | IDEAL_RAOULT_NOT_ACCURACY_VALIDATED |
| C11-REQ-008 | matrix mass and mole conservation | PASS | DECLARED_MATRIX_AND_ANALYTIC_BASELINE |
| C11-REQ-009 | uncertainty propagation | PASS_NONSTATISTICAL_SENSITIVITY_ONLY | NO_EMPIRICAL_CALIBRATION |
| C11-REQ-010 | dynamic conservation and nonnegativity | PASS | UNVALIDATED_SIMULATION_ONLY |
| C11-REQ-011 | substrate separation | PASS | EXACT_SUBSTRATE_MODEL_BINDING_NO_CROSS_TRANSFER |
| C11-REQ-012 | leakage prevention | PASS | PRESPECIFIED_SPLIT_AND_MODEL_LOCK |
| C11-REQ-013 | benchmark reproducibility | PASS_ANALYTIC_AND_DETERMINISTIC_ONLY | NO_EMPIRICAL_PERFORMANCE_BENCHMARK |
| C11-REQ-014 | applicability and abstention | PASS | ANSWERLESS_FAIL_CLOSED_ABSTENTION |
| C11-REQ-015 | natural-lot precedence | PASS_CONTRACT_ONLY_NO_REAL_LOTS | EXACT_SIX_LEVEL_PRECEDENCE |
| C11-REQ-016 | area-percent safeguards | PASS | AREA_PERCENT_NEVER_CONCENTRATION |
| C11-REQ-017 | projection separation | PASS | OLFACTORY_REGULATORY_AUTHENTICITY_SEPARATE |
| C11-REQ-018 | interaction context | PASS_WITH_NUMERIC_EFFECTS_WITHHELD | CONTEXT_SPECIFIC_RECORDS_NO_GENERIC_MULTIPLIER |
| C11-REQ-019 | constrained optimizer feasibility | PASS_SOFTWARE_FEASIBILITY_ONLY | HARD_GATES_BEFORE_SCORING_AND_EXACT_HASH_HUMAN_REVIEW |
| C11-REQ-020 | historical 30k regression | BLOCKED_MISSING_REPRODUCIBLE_ARTIFACT_BUNDLE | CORRECT_FAIL_CLOSED_NONPROMOTION |
| C11-REQ-021 | negative claims | PASS_WITHHELD | UNSUPPORTED_OUTCOMES_REQUIRE_EXACT_BUILD_D_RECEIPT |
| C11-REQ-022 | API and report provenance | PASS | DETERMINISTIC_LOCATOR_PRESERVING_REPORTS |
| C11-REQ-023 | export, import, backup, and restore | PASS | PORTABILITY_AND_RECOVERY_SOFTWARE_CONTRACT |

All 23 requirement categories are accounted for. A `PASS_ABSTENTION` or `BLOCKED` row means the required fail-closed behavior was reproduced; it is not a claim that the absent scientific model or dataset exists.

## Model inventory and consolidation

- C0 implementations inventoried: `48`
- Classification counts: `{"DISCONNECTED_LEGACY": 3, "EXACT_PHYSICAL_ARITHMETIC": 4, "HEURISTIC": 32, "LITERATURE_DERIVED_MODEL": 3, "STUB": 3, "UNSUPPORTED": 3}`
- Canonical future interface: `engine.physics versioned request/result router`
- Current headspace adapter: `engine.pipeline.formula_state.build_formula_state`
- Current dynamic adapter: `engine.pipeline.simulator.simulate_formula`
- Unsupported-output policy: `WITHHELD`

UNIFAC remains an inactive/data-only stub; COSMO-RS and DIPPR-style execution are absent. The only executable C4 equilibrium model is `c4-ideal-raoult-v1`, a theoretical ideal Raoult baseline. Henry, empirical matrix correction, UNIFAC, and COSMO-RS releases remain unavailable.

## Property, matrix, and applicability coverage

- Thermophysical property vocabulary: `16` closed properties.
- Vapor-pressure representation tags: `6`.
- Equation evaluator implemented: `false`.
- Real property observations promoted by B2: `0`.
- Matrix stages: `5`; environment kinds: `9`.
- Applicability behavior: exact release selection, immutable version binding, explicit fallback disclosure, and answerless abstention.

## Calibration, split, metrics, and uncertainty

- Representative materials: `19` across `10` material classes.
- Matrix templates: `8`.
- Partitions: `CALIBRATION, VALIDATION, HELD_OUT_TEST`.
- Leakage dimensions: `chemical_identity_group, close_analog_group, formula_id, supplier_lot, matrix_batch_id, measurement_session_id`.
- Required metrics: `bias, mae, rmse, median_absolute_fold_error, rank_agreement, calibration_slope, calibration_intercept, prediction_interval_coverage, catastrophic_outlier_rate, missing_domain_rate, abstention_rate, rmse_improvement_vs_baseline`.
- Metrics by material class and matrix: `NOT_COMPUTED_NO_REAL_DATA`.
- Empirical abstention rate: `NOT_COMPUTED_NO_REAL_DATA`.
- C4 uncertainty: `UNKNOWN`; C6 uncertainty: deterministic parameter sensitivity, not a statistical interval.

## Dynamic, lot, interaction, and optimizer boundaries

- C6 enforces nonnegative, per-component/per-frame mass-conserving simulation with separate substrate models; its authority is `UNVALIDATED` and `SIMULATION_ONLY_UNCALIBRATED`.
- Natural-lot precedence: `EXACT_LOT_QUANTIFIED, EXACT_LOT_RELATIVE_PROFILE, SUPPLIER_BATCH_SPECIFIC, SPECIFIC_LITERATURE_PROXY, GENERIC_MATERIAL_PROXY, UNKNOWN`.
- Normalized GC area percent is concentration: `false`.
- Projection families remain separate: `OLFACTORY_HEADSPACE, REGULATORY_ALLERGEN, IDENTITY_AUTHENTICITY`.
- Generic numerical interaction adjustment allowed: `false`.
- C10 hard feasibility gates run before scoring, objectives remain separate, and an exact-content-hash human PASS receipt is required before execution.

## Verification outcome

- C0-C10 focused: `655 passed.
- Root suite: `1753 passed.
- Backend portability/provenance: `16 passed.
- Backend full: `630 passed.
- Synthetic archive-verifier contract: `7 passed.
- Runtime mypy: `PASS_20_SOURCE_FILES`; basedpyright, Ruff lint, compileall, pip checks, SQLite quick checks, protected-state comparison, and log hygiene passed.

The broad Ruff-format diagnostic is inherited committed style drift in seven clean files. The broad mypy diagnostic is 96 test-fixture typing errors in five test files, with no runtime-source error. The old C9 archive contract test is invalid for the later live checkout; a state-independent seven-case C11 synthetic contract replaced it. No production or C11 source was changed to hide these diagnostics.

## Permitted wording

- Build C software contracts and aggregate verification passed for the tested source state only after the C11 committed replay and final seal are recorded.
- The executable equilibrium calculation is a theoretical ideal Raoult comparison baseline with analytic tests; it is not an accuracy-validated perfume headspace model and cannot feed OAV screening.
- Dynamic release is an unvalidated, simulation-only deterministic sensitivity model with conservation and nonnegativity checks; it is not measured perfume performance.
- Natural-lot, interaction, OAV, receptor, adaptation, aging, and optimizer contracts fail closed when exact evidence or context is absent.
- No real instrument observations, real natural-lot profiles, held-out C10 outcomes, or reproducible historical 30k artifact bundle were available; empirical metrics were not computed and scientific release remains blocked.

## Forbidden wording

- Build C proves accurate real-world perfume headspace, longevity, sillage, projection, intensity, pleasantness, preference, or receptor response.
- UNIFAC, modified UNIFAC, COSMO-RS, DIPPR-style equations, or empirical matrix correction are implemented or validated.
- Normalized GC area percent is constituent concentration or regulatory mass fraction.
- The historical 30k candidates, 35 guardrails, and 97.76 result were reproduced or are canonical.
- Build D has started or is authorized by this draft report.

## Next gate

`Run a fresh exact-project DeepLuna Fast audit of the generated C11 packet, reconcile it locally, validate and commit only C11-owned evidence, create a Git-blob manifest, replay the exact commit in a clean detached worktree, then record the Build C boundary decision. Do not begin Build D.`
