# Formulation performance acceptance — 2026-09-15

## Decision

KEEP the material-name normalization change in `engine/name_utils.py`.
Replace regex whitespace collapsing with `" ".join(name.split()).lower()`;
continue resolving aliases from the live dictionary on every call. No persistent
cache, scientific calculation, dose constraint, gate, or release permission changes.

The user's acceptance criterion was measured compute/validation time reduction;
remove experimental changes that do not earn their cost. Only this production
change survived the trials. The broader workflow/integration proposals were not
implemented because these measurements did not justify them.

## Final paired benchmark

Receipt: `output/performance_20260915/acceptance.json`.
Reproducer: `tests/test_formulation_performance.py` (explicit opt-in).

| Workload | Before median | After median | Time reduction | Faster pairs |
|---|---:|---:|---:|---:|
| Score 40 distinct candidate vectors | 242.84 ms | 192.18 ms | 20.86% | 12/12 |
| Global search: baseline + 24 proposals + 24 random controls | 427.26 ms | 363.21 ms | 14.99% | 11/12 |
| All formula gates plus unified release scoring | 203.16 ms | 198.31 ms | 2.39% | 10/12 |

Each workload used twelve paired before/after samples with alternating order.
Every complete serialized output matched its workload's reference SHA-256.
The receipt binds engine, material, inventory/governance, knowledge-graph and
benchmark inputs and verifies that those bytes did not change during measurement.

The benchmark runs the original regex function body and the new function body
through the same imported function object, restoring it in `finally`. Aliases,
inputs, seed, worker count, evaluator, and verification scope are unchanged.
Formula-state caches are cleared before every timed arm. Imports, registry and
rule indexes are warmed. Candidate vectors remain alive to avoid confounding
the existing scorer's object-identity caches with object-ID reuse.

The acceptance threshold was at least 5% faster scoring and search, each faster
in at least 9/12 pairs, with no validation slowdown exceeding 5%. It passed.
The small validation improvement is secondary; it is not a large validation gain.

### Scope limits

- These are synthetic regression compositions exercising real scoring/search
  and formula-gate implementations, not released or bench-ready perfumes.
- Results measure warmed computation. Interpreter startup, CLI parsing,
  evidence hashing, audit-file writing and report rendering are not timed.
- The validation fixture disables audit writes; it still executes all gates.
- No physical compounding, maturation, sensory outcome, or full-project release
  speedup is established. The current stock-bound Gin Vetiver CLI remains blocked
  by the pre-existing source-drift failures below.

## Discarded trials

- Inventory parsing memo within one call: approximately 2% median materialization
  gain amid noise; not retained (`inventory_local_memo_benchmark.json`).
- Rule-object deduplication: approximately 2.15% scoring gain; not retained
  (`rule_dedup_trial.json`).
- Reading YAML into strings first: stabilized measurements did not support a
  reliable gain; not retained.
- Lazy profile construction was not adopted because it could skip existing
  malformed-profile checks. Additional file-fingerprint caching was not justified
  by the profile: that path ran once and took approximately 1 ms.

Trials used temporary in-process alternatives. No rejected production changes,
new runtime pipeline scripts, or cache services remain.

## Verification

- First focused suite: 92 passed, 3 failed. All three failures are in
  `tests/test_global_design_cli.py` and raise `Design plan source drift: rebind
  against current formula/inventory`.
- Re-executing those three tests with the original `HEAD` normalization body
  reproduced all three failures. Stored authority pins were not changed.
- Additional pre-mix, inventory-alias, identity, gate and normalization coverage:
  74 passed, 1 intentionally skipped opt-in performance test. This group overlaps
  the first group; counts must not be added as unique tests.
- Opt-in performance acceptance: 1 passed.
- Focused Ruff and `git diff --check`: passed.
- Normalization tests cover all Unicode whitespace characters across the alias
  corpus, non-whitespace characters, empty input and live alias updates.
- Full project/release verifier not run; this is scoped performance acceptance.

## Reproduce

```powershell
$env:PERFUME_RUN_PERFORMANCE = '1'
$env:PYTHONHASHSEED = '0'
.venv/Scripts/python.exe -m pytest tests/test_formulation_performance.py -q -s
Remove-Item Env:PERFUME_RUN_PERFORMANCE
Remove-Item Env:PYTHONHASHSEED
```

The performance test is skipped in ordinary test runs to avoid increasing
routine validation time. Benchmark receipts are generated under `output/`.

## Technical basis

Python documents that `str.split()` without a separator collapses runs of
whitespace and drops leading/trailing empty fields. Unicode regex `\s` uses
the Unicode whitespace predicate. The compatibility tests verify the transition
on the actual interpreter.

- https://docs.python.org/3/library/stdtypes.html#str.split
- https://docs.python.org/3/library/re.html
