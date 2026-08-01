# Build A Phase A1 Authoritative Exit Gate

Date: 2026-08-01

Authority: the current `D:\chatbots\perfume-chem` working tree, executable
tests, the canonical repository verifier, and the A1 requirements at master
prompt lines 998-1220. The superseded 2026-07-29 report was historical only.

## Baseline and recovery

- A0 exit gate: passed.
- A1 starting SHA: `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435`.
- Supported test runtime: Python 3.11 in `.venv_py311_a0`.
- A1 pre-edit archive:
  `a1_preedit_20260801_052345.tar`.
- Archive SHA-256:
  `d66bc0ef45285fbb6a3893014fc5842f0359cdf47ddee51a9376a946f28f01d8`.
- Manifest SHA-256:
  `4d6b280921967e08730d8299598f46f34dda12393655416157854eab9386a527`.
- Verification: 12 source paths restored with zero byte/hash mismatches at
  `C:\A1P_20260801_052345`.

## Reproduced test sequence

| Stage | Result | Evidence |
|---|---:|---|
| Historical A1 pair, fresh first run before edits | 75 passed | `verification_runs/a1_contracts_first_run.xml`; JUnit SHA-256 `efd1f28f09de2c19477d43c8f84885b04a75025aec40e9f7ba590d00892da855` |
| Strengthened contracts before production fixes | 87 passed, 6 failed | `verification_runs/a1_contracts_red.xml`; JUnit SHA-256 `20ba3a249c229046a50c2b556ec84e556ae627d7698cb2445b256a6ecd419fb1` |
| Final A1 contract pair | 97 passed | `verification_runs/a1_contracts_final.xml`; JUnit SHA-256 `6f20557b8280bc4341e1910bf2388fa3091e2469adf24e67608b9cb3bc4e0dbc` |
| A1 plus directly affected legacy modules | 117 passed | `test_reconstruction_anti_compression.py`, `test_reconstruction_quantity.py`, and `test_reconstruction_ensembles.py` included |
| Shard manifest uniqueness | 1 passed | `tests/test_project_verification.py::test_engine_shards_cover_every_test_file_once` |

The RED result contained six pytest failures because one chemical-identity
contract was parameterized over three dimensions. It reproduced four defect
classes:

1. same CAS incorrectly returned `MATCH` despite different declared
   stereochemistry, natural origin, or chemotype;
2. same CAS and supplier grade incorrectly returned `MATCH` despite different
   declared lots;
3. two `restore_from_roster` empty-input paths plus empty uncertainty scaling
   and empty quantity reconciliation returned normally;
4. a zero quantity-reconciliation denominator returned unchanged data instead
   of a stable domain error.

## DeepLuna gap-audit disposition

Fresh exact-project health was `READY`, Fast-only, with no queue, reservation,
or unavailable circuit. Bounded read-only job
`DS-bbc94fa53407e67f374424a6aba4ab9f` returned `PASS` and claimed no A1 gaps.
Sol rejected that conclusion because the cited implementation contradicted it:

- `engine/reconstruction/anti_compression.py::_check_same_cas` compared CAS but
  ignored its own `stereochemistry` profile field and all natural identity
  dimensions;
- `_check_same_supplier_grade` compared only `supplier_grade` and ignored lots;
- `restore_from_roster`, `scale_uncertainty_to_ensemble`, and
  `reconcile_total` lacked required empty-input guards;
- `reconcile_total` silently accepted a zero denominator.

The worker made no edits and retained no authority over A1 acceptance.

## Contract disposition

| Contract | First-run disposition | Strengthened/RED result | Minimal source change | Final result | Verifier impact |
|---|---|---|---|---|---|
| A1.1 diluent-aware accounting | Existing tests passed; implementation already separated declared active/carrier/ethanol/water/unallocated and conserved raw amount. DEP and IPM had classifier-only coverage. | New parameterized 10% full-accounting cases for DPG, DEP, TEC, and IPM were GREEN. | None. Retained the existing declared-composition path and compatibility name parser. | PASS | Four additional parameter instances in gates/families shard. |
| A1.2 target-row preservation | Existing round-trip test passed but directly compared only a subset of accepted fields. | Strengthened assertion compares every supplied row field against constructed output, then verifies `TargetMaterial` serialization round-trip. GREEN without source change. | None. | PASS | Stronger direct losslessness proof; no schema change. |
| A1.3 twelve-axis anti-compression | Existing 12-axis/tri-state cardinality tests passed, but existence-only historical tests and CAS-only identity checks did not prove stereoisomer, natural identity, lot, or physical-stock separation. | RED for three chemical dimensions and lot. Scope-specific differences, conclusive MATCH/UNKNOWN behavior, neat-vs-dilution, and tri-state compatibility are now explicit. | Added one declared-dimension comparator. Chemical axis now requires CAS plus conclusive declared stereo/natural identity evidence and returns `DIFFER` on declared conflicts. Supplier axis now compares supplier, product, grade, purity, and lot when declared. The public 12-axis API is unchanged. | PASS | Four defect-producing parameter instances plus conclusive positive/unknown cases added. |
| A1.4 chained correction replay | Missing/cross-stream/cycle/stale/conflicting retry, three-link latest-wins trace, immutable input, and idempotent retry all passed. | No absent behavior found. Confirming tests retained. | None. | PASS | No source change. |
| A1.5 empty reconstruction inputs | Seven primary entry points, zero budgets, and rank-prior denominator guards passed; the suite did not exercise roster restoration, uncertainty scaling, or quantity reconciliation. | RED identified four accepting paths and the zero reconciliation denominator. | `restore_from_roster` rejects empty compressed/full rosters; `scale_uncertainty_to_ensemble` rejects an empty base target; `reconcile_total` rejects empty targets, non-positive/non-finite target totals, and non-positive/non-finite denominators with `ReconstructionInputError`. | PASS | Full public-entry contract test and focused zero-denominator test pass; no raw arithmetic exception. |
| A1.6 identity vs inventory | Independent enum sets and exact/alias/unresolved, exact lot, absent stock, grade mismatch, and functional substitute behavior passed. | Added direct AMBIGUOUS/NO_SUITABLE_STOCK and EXACT/NOT_TECHNICALLY_REQUIRED assertions. GREEN without source change. | None. Legacy flat statuses remain compatibility projections only. | PASS | Two behavior tests added. |
| A1.7 identity conservatism | Same-CAS grade/lot, natural origin, controlled grade, opaque-base, missing-CAS, and registered trade-material tests passed. | Anti-compression tests now independently prove declared natural identity and lot differences are not hidden by CAS. | No identity-resolver change. | PASS | Cross-layer confirming coverage strengthened. |
| A1.8 strengthen, do not replace | Historical tests included result-exists and bool-only assertions. | Existing neat/dilution test now asserts a `DIFFER` roster axis and no merge; Hedione/HC now asserts supplier-grade `DIFFER`; bool compatibility test now asserts all MATCH/DIFFER/UNKNOWN enum results. No tests were deleted. | Test changes only. | PASS | Existing coverage became semantically stricter. |

## Before/after assertion rationale for edited tests

1. `test_target_row_round_trip_preserves_authoritative_fields`
   - Before: compared a selected field list.
   - After: compares every supplied accepted field and the complete serialized
     round trip. This is stricter because newly accepted fields cannot be lost
     silently outside a hand-maintained assertion subset.
2. `test_neat_and_dilution_are_different_stocks`
   - Before: asserted only that an audit result existed.
   - After: requires `source_roster_identity=DIFFER` and `should_merge=False`.
3. `test_audit_detects_cas_similarity_as_not_mergeable`
   - Before: asserted only that an audit result existed.
   - After: provides same-CAS declared profiles, requires supplier-grade
     `DIFFER`, and requires no merge.
4. `test_compression_check_three_valued`
   - Before: checked the legacy boolean view for true and false.
   - After: also requires canonical MATCH, DIFFER, and UNKNOWN results and
     verifies UNKNOWN does not pass.
5. `test_all_public_reconstruction_entry_points_reject_empty_inputs`
   - Before: seven calls were checked sequentially, so an early miss could
     hide later omissions.
   - After: thirteen primary calls are evaluated and every missing domain
     error is reported together.

## Canonical full verifier

Command:

```text
.venv_py311_a0\Scripts\python.exe scripts\pipeline_audit.py project-verify --json
```

Result:

- process exit: 0;
- duration: 814 seconds;
- stdout SHA-256:
  `25afff1f7a449276c693b3702d9e77da59dc0ce64b66bbdb7f62f0f1365ed983`;
- stderr: empty, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- canonical report SHA-256:
  `c3c6dfab1097363b8516dc048de6f3dc05e23be68bbb6575f586e767850d99f0`;
- scope: `full`;
- completion gate: `PASS_WITH_SKIPS`;
- required checks: 19 PASS, 0 FAIL;
- skips: Docker build and smoke only, because `--include-docker` was not
  requested;
- omitted checks: none;
- formula artifact and reviewed golden-fixture lock: PASS/unchanged.

Test counts from the verifier JUnit files:

| Shard | Tests | Failures | Errors | Skips |
|---|---:|---:|---:|---:|
| engine truth core | 189 | 0 | 0 | 0 |
| engine data/knowledge | 235 | 0 | 0 | 0 |
| engine gates/families | 602 | 0 | 0 | 0 |
| engine legacy | 69 | 0 | 0 | 0 |
| **engine total** | **1,095** | **0** | **0** | **0** |
| backend complete | 629 | 0 | 0 | 0 |
| **combined executable count** | **1,724** | **0** | **0** | **0** |

`engine-typecheck` and `backend-typecheck` passed in the canonical verifier.
A separately scoped mypy invocation over the pre-existing untracked
`quantity_inference.py` reports the same two loop-variable typing warnings in
both the pre-edit restore and current file; they are baseline, not A1
regressions.

## Schema and release boundaries

- No migration, model, schema, repository, or database file was changed by A1.
- A1 changed pure reconstruction contracts and tests only.
- Laboratory Beta remains ready.
- Scientific release remains independently blocked by held-out sensory
  validation; A1 does not alter or bypass that gate.

## Final DeepLuna Fast validation

After a fresh standalone exact-project preflight returned `READY` for
`project_id=perfume-chem`, bounded read-only Fast job
`DS-f54292eec1f6ec53ad9d6e56cb03f079` audited this report against selected
implementation, test, plan, and machine-readable verifier ranges.

- route: `FLASH` only, one provider call, `NO_LUNA`, no alternate provider;
- provider permissions: read-only; no Git, file writes, secrets, databases,
  caches, architecture, science, release, or final-acceptance authority;
- terminal status: `PASS` / `POSITIVE` / `ACCEPTED`;
- contradictions or unsupported claims: none reported;
- count reconciliation: 97 final A1 contracts, 1,724 combined executable
  tests, and 19 required verifier checks passed;
- scope deviation: false.

Sol independently re-parsed `verification_runs/project_verification.json`,
re-read the cited implementation and test ranges, and accepted the worker's
mechanical result. The worker did not grant A1 acceptance.

## Exit decision

Implementation, repository verification, and final Fast-validation gates are
PASS. The A1 exit becomes immutable when a bounded A0/A1 checkpoint containing
this report is committed. That commit's SHA is the external gate identifier;
unrelated tracked and untracked work is excluded and preserved in place.
