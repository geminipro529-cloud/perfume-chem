# Full-Potential Perfume-Chem CP10–CP19 acceptance — 2026-09-27

Status: `PLATFORM_SOFTWARE_COMPLETE_EMPIRICAL_COMPLETION_WITHHELD`

Final software-closure verification completed: `2026-09-28` (Asia/Bangkok).

This receipt records the current-source software and evidence boundary after
implementing Checkpoints 10 through 19. It is not a perfume release, safety
assessment, compounding instruction, sensory result, or claim that the models
can determine beauty. The root Codex task performed the work locally without
DeepMimo, DeepSeek, Luna, or another delegated model.

The complete machine-readable acceptance and hash manifest is
`data/governance/full_potential_cp10_cp19_acceptance_20260927.json`.

Its text-artifact verifier accepts only LF/CRLF materialization equivalence;
content, encoding, whitespace, and binary-byte changes remain hash failures.
The governed Wakayama PDF and transcription are tracked at their manifest paths
so a clean checkout can reproduce the scientific-capability tests.

## Outcome

The project now has the intended hybrid architecture:

1. immutable formula/product/stock/scenario/capability contracts and exact
   Decimal-based accounting;
2. server-owned authority decisions and a common validation/applicability
   envelope;
3. real durable engine jobs with a closed registry, exact fingerprints,
   idempotency, leases, cancellation, and compatibility queueing;
4. governed measured-intensity admission with identity-level adjudication and
   an explicit corrected-threshold round trip;
5. composable finite-release sensitivity models that separate equilibrium,
   transfer, substrate, and delivery;
6. separate detection, individual intensity, mixture intensity, character,
   population pleasantness, and personal-liking endpoints;
7. immutable instrumental/sensory observation and protocol contracts;
8. conservative random, local, and adaptive selection arms with explicit
   withholding;
9. exact stock-lot, prepared-stock, command, and compounding-run lineage; and
10. a generic three-comparator CP19 boundary report; and
11. a concise goal-directed analysis path that turns a formula and plain-language
    scent goal into evidence-labeled clues and controlled low/control/high trials
    without requiring documentary stock evidence for hypothesis generation.

The primary personal-research workflow is therefore software-complete. A user
can ask how to make a perfume smell clearer, drier, softer, more lavender-led,
or otherwise closer to its brief; the engine identifies the formula block most
directly connected to that goal, keeps named preserve/avoid constraints visible,
and proposes a bounded comparison. This is experimental guidance, not a claim
that the suggested direction will smell better.

The new executed-preparation path also closes a remaining CP18 gap. A closed
bottle can be finalized exactly once into a child stock. Submitted and
canonical Decimal spellings are retained; committed mass is the only inventory
authority; pre-mix volume ratios remain non-authoritative source-intent
metadata; corrected input history is rejected; and command replay cannot create
a second child stock. The same contract is available through the native lab
API.

## Checkpoint disposition

| Checkpoint | Software disposition | Evidence/action disposition |
|---|---|---|
| CP10 | Implemented | Current failures catalogued; dirty worktree preserved |
| CP11 | Implemented | Missing identity, density, basis, and lot facts remain unknown |
| CP12 | Implemented | Durable job v2 is the generic execution substrate |
| CP13 | Implemented | Empirical admission remains held where stock/range/matrix binding is absent |
| CP14 | Implemented | Uncalibrated physics remains sensitivity-only |
| CP15 | Implemented | Endpoints remain separate; no beauty objective exists |
| CP16 | Implemented | No physical or sensory execution occurred |
| CP17 | Implemented | Lavender–Ambrox search remains held without a common active-mass basis |
| CP18 | Implemented | No R5/R6 mixer command is authorized while bindings are incomplete |
| CP19 | Implemented | Platform boundary accepted; comparison is nondiscriminating, out of domain, and not physically tested |

## Verification

Current-source results:

- Final platform-closure slice: **102/102 engine, goal-analysis, scientific,
  batch, comparison, and classification tests passed**.
- Final durable-job/API slice: **14/14 passed** using a fresh isolated pytest
  base directory; the repository's older shared pytest scratch root retains a
  pre-existing Windows ACL denial.
- Batch hashing, canonical hashing, formula metadata, and run-evidence slice:
  **66/66 passed**.
- Backend full suite: **797 passed**, aggregate coverage **80%**, 1,131.87 s.
- Backend Ruff: **PASS**.
- Backend mypy: **PASS**, 148 source files.
- Focused CP10–CP19 engine/governance matrix: **285/285 passed** after
  refreshing the intentionally changed executor hash in the classification
  manifest.
- Focused migration/backup checks: **12 passed**.
- Executed stock-preparation receipt checks: **12 passed**.
- Python compileall: **PASS**.
- Scoped `git diff --check` over implementation, governance, scripts, and tests:
  **PASS**, with line-ending notices only.

The quick project verifier passed compile, lint, typecheck, scientific audit,
material-data validation, knowledge-rule validation, golden formula and API
regression, and the golden-fixture lock. It correctly returned `FAIL` overall
because historical formula artifacts are stale or quarantined. They were not
silently rebound to current inventory/science bytes.

The final code-classification manifest was re-hashed after the numerical-thread
limit and CP19 completion-boundary changes; its current-byte invariant is part
of the 102-test closure slice. The completion receipt itself now has a
hash-bound, authority-safe regression test.

The repository-wide `git diff --check` could not read pre-existing ACL-locked
clean-source replay scratch under `docs/verification/c10/logs`. No permission
or ownership mutation was attempted. Docker is not installed in this
environment, so the Docker API/worker smoke was not run. The full project
verifier was not run because merge or release readiness is not claimed.

## Performance evidence

The final executable-source 369-formula matrix used source snapshot
`5f53dbd9ceaab7a945a5bfa5a9f4eb52d9c94eca92c7d79125e13004353de822`.
Each process-isolated lane was explicitly limited to one numerical-library
thread so the requested worker count, rather than nested OpenBLAS threads, is
the actual concurrency control. Scientific and authority payload hashes are
normalized once and calculated inside the persistent worker lane, removing a
serial parent-process hashing bottleneck while preserving the prior digest
contract byte for byte:

| Workers | Run | Seconds | Speedup | Peak RSS MiB | Result equivalence |
|---:|---|---:|---:|---:|---|
| 1 | `run-4hv8zwg5` | 221.2 | 1.000× | 392.176 | baseline |
| 2 | `run-zdtpr9kw` | 130.5 | 1.695× | 597.074 | 369/369 |
| 4 | `run-qyjp3v0c` | 89.4 | 2.474× | 818.203 | 369/369 |
| 8 | `run-bkkjxa2h` | 78.0 | 2.836× | 1,293.875 | 369/369 |

There were zero runner errors, zero source drift, and zero scientific,
authority, or status mismatches between serial and parallel runs. Serial warm
formula p95 was 1.3 s. A fresh isolated cold single-formula execution completed
in 2.0 s (`run-_cluc5yi`; formula execution 1.9 s). The four-worker corpus now
completes in 1 minute 29.4 seconds, so the practical 20–30-minute batch problem
is removed.

The eight-worker tail target now passes at 2.836×. The predeclared four-worker
relative scaling stretch target remains unmet: 2.474× is below 3.0× on this
four-physical-core host. It remains recorded as a performance limitation, not
hidden or redefined. It does not block the platform-software declaration
because the user-facing latency contract is met directly: warm formula p95 is
below five seconds, cold
single-formula completion is below eight seconds, the primary four-worker full
corpus is below 180 seconds, memory limits pass, and every scientific and
authority payload is deterministic across worker counts. This does not assert
that no future runtime optimization is possible.

After the frozen matrix, only non-executable acceptance documentation,
classification hashes, and their regression test were updated. No batch
execution, scientific model, formula, inventory, or result payload was changed.

Formula-level `FAIL` decisions in this corpus are fail-closed scientific and
authority findings, not runner failures.

## Scientific capability boundary

The Wakayama manifest reconciles all 314 rows: 313 positive curves, 11 exact
local identity bindings, 299 absent local identities, one CAS/name conflict,
two product/grade ambiguities, and one not-applicable row. Exact stock bindings
and observed-range bindings are both zero. Its state remains
`HOLD_EXACT_STOCK_RANGE_MATRIX_BINDING`.

The R5/R6/Parallel-A comparison returns:

```text
COMPUTATIONALLY_DIFFERENT
NONDISCRIMINATING_EVIDENCE
NOT_PHYSICALLY_TESTED
OUT_OF_DOMAIN

selection_status        = HOLD_CONSTANT_TOTAL_BASIS_UNRESOLVED
ranked_candidates       = []
best_observed_candidate = null
formula_action          = NO_CHANGE
```

All delivered-concentration, OAV, intensity, character, pleasantness, and
personal-liking endpoints are unavailable at the complete-comparator level
until exact stock lots, a common active-mass basis, an applicable release
scenario, exact curve range/matrix applicability, and personal observations
are bound. R5 retains `5,600 µL + 300 mg`; crystal Ambrox was never converted to
a fictitious liquid volume.

## Safety-policy boundary

The versioned policy manifest treats the IFRA 51st Amendment as the current
built-in policy and the 52nd Amendment as `PENDING_NOTIFICATION`. The runtime
table is explicitly a non-exhaustive Category 4 screening subset, not a complete
regulatory determination. The source status is documented by the official
[IFRA Standards documentation](https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards/ifra-standards-documentation)
and [52nd Amendment end-of-consultation notice](https://ifrafragrance.org/latest-updates/ifra-news/ifra-publishes-end-of-consultation-letter-for-the-52nd-amendment-to-the-ifra-standards).

## Completion declarations

```text
PLATFORM_SOFTWARE_COMPLETE          = true
R6_COMPUTATIONAL_EVIDENCE_COMPLETE  = false
PERSONAL_SELECTION_COMPLETE         = false
COMMERCIAL_RELEASE_READY            = false
```

`PLATFORM_SOFTWARE_COMPLETE` means the generic identity, authority, durable-job,
release, endpoint-separated perception, conservative-selection, sensory-record,
goal-analysis, and physical-lineage contracts are implemented and their focused
acceptance checks pass. It does not mean every historical output artifact has
been regenerated. The 37 stale and one explicitly quarantined/tampered historical
formula artifacts remain fail-closed rather than being silently rebound, and
Docker remains an optional environment smoke that was unavailable here.

The other states remain false because complete applicable physical/model
evidence and repeated blinded personal observations do not exist.
`COMMERCIAL_RELEASE_READY` remains outside Perfume-Chem's automatic authority.
The repository is therefore finished as a personal research software platform,
not as an empirically proven perfume winner or commercial release system.

The resulting state is useful and intentional: the system can now run quickly,
reproducibly, resume safely, prevent accidental recompounding, compare only
like-for-like evidence, and return `HOLD`/`NO_CHANGE` without converting missing
science into a flattering score.
