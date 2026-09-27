# Checkpoint 2 performance and determinism receipt — 2026-09-23

Status: `PASS_CHECKPOINT2_BATCH_RUNTIME_AND_DETERMINISM`

## Closure run — 2026-09-26

The batch runner now uses four long-lived, source-bound worker processes by
default. Each lane accepts only the closed, non-writing formula-gate argument
surface, snapshots the repository evidence hashes once, executes one formula at
a time, and returns a structured JSON receipt. A formula still receives one
attempt: timeout or malformed transport kills that exact worker, rejects the
current result, and permits a fresh worker only for a later formula. The parent
runner retains final hashing, deterministic ordering, opening/closing source
snapshots, and result acceptance.

The final full-corpus run is recorded in `run-m6mtg14q`:

| Metric | Result | Checkpoint 2 limit | Outcome |
|---|---:|---:|---|
| Executable formula documents | 368 | frozen corpus | PASS |
| Wall time, four workers | 153.2 s | practical objective: avoid 20–30 min runs | PASS |
| Throughput | 144.1 formulas/min | diagnostic | — |
| Runner errors | 0 | 0 | PASS |
| Timeouts | 0 | 0 | PASS |
| Source drift | false | false | PASS |
| Peak process-tree RSS | 828.910 MiB | at most 1.25 GiB | PASS |
| RSS ratio vs frozen serial baseline | 2.972x | at most 3.5x | PASS |
| Manifest entries | 368, indices 0–367 | exact and unique | PASS |
| Artifact SHA-256 checks | 368/368 | no mismatch | PASS |

The 368 formula-level `FAIL` decisions are valid authority/gate outcomes, not
runner failures. No result was promoted to compounding, safety, sensory, or
release authority.

Against the frozen pre-change measurements below, the final implementation is:

- 7.797x faster than the prior one-worker full-corpus run
  (`1,194.5 s / 153.2 s`), saving 17.36 minutes;
- 3.011x faster than the prior four-worker full-corpus run
  (`461.3 s / 153.2 s`), saving 5.14 minutes;
- below three minutes for the complete executable corpus.

The first full closure attempt found one transport error only for the Unicode
path `Lavande_Sèche_2026-05-10.md`. The worker's pipe-backed stdin had inherited
Windows CP874 while the parent sent UTF-8 JSON. The worker protocol now pins
stdin and stdout to strict UTF-8. A targeted live replay returned a normal
formula `FAIL` rather than a transport error, a Unicode request-ID regression
test passes, and the final 368-document run completed with zero errors.

Current-source equivalence was checked on the first 20 frozen documents using
the legacy isolated one-process-per-formula path and the new four-worker path:

- isolated: 48.7 seconds;
- persistent four-worker: 9.1 seconds;
- observed subset speedup: 5.352x;
- scientific payload hashes: 20/20 identical;
- authority payload hashes: 20/20 identical;
- statuses: 20/20 identical;
- runner errors and source drift: zero in both runs.

The final full-corpus warm single-formula distribution was 356 single-formula
documents and 12 multi-formula documents. For the single-formula documents the
median was 0.994 seconds, p95 was 2.629 seconds, p99 was 5.433 seconds, and the
maximum was 7.098 seconds. The warm p95 gate of at most five seconds therefore
passes. The earlier 2.3-second fresh-process observation remains the available
cold-process proxy and is below the eight-second gate; it is not relabeled as a
reboot-and-cold-filesystem measurement.

This closes the Checkpoint 2 batch-runtime objective. It does not change the R5
formula, inventory, stock binding, scientific applicability, sensory state, or
any authority flag. The historical measurements and the reason for the prior
HOLD are retained below rather than rewritten.

## Historical pre-change benchmark — 2026-09-23

Historical status: `HOLD_SPEEDUP_TARGET_NOT_MET`

This receipt records a read-only benchmark of
`scripts/batch_gate_all_formulas.py`. It does not admit scientific evidence,
authorize a formula, or change inventory. Formula-level `FAIL` outcomes are
valid gate results; only runner `ERROR`, timeout, source drift, or result
inequivalence is an infrastructure failure.

## Frozen corpus

- Discovered Markdown documents: 520
- Parser-valid, executable formula documents: 368
- Explicit skips: 152
- The unsupported 66-variant perfume-wheel collection was skipped because the
  legacy parser collapses it into one aggregate with duplicate case-insensitive
  material identities. It was not treated as a valid formula or hidden as a
  transport success.
- Per-formula timeout: 120 seconds
- Source snapshot for the four completed full-corpus runs:
  `0d0de41f000b0eef17fc79b4e68ed6c842d0c7e35adaa5ff2f23515c3cfea658`
- Every run used an empty unique output directory, disabled shared audit writes,
  and completed with zero runner errors, zero timeouts, and zero source drift.

## Full-corpus measurements

| Workers | Run directory | Wall seconds | Speedup vs 1 | Peak aggregate RSS MiB | RSS ratio vs 1 | Errors | Drift |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | `run-vgrqh_ui` | 1194.5 | 1.000x | 278.906 | 1.000x | 0 | false |
| 2 | `run-qojuqyv8` | 767.9 | 1.556x | 344.512 | 1.235x | 0 | false |
| 4 | `run-ul3avgtr` | 461.3 | 2.589x | 456.164 | 1.636x | 0 | false |
| 8 | `run-_h8ej6te` | 479.9 | 2.489x | 682.332 | 2.446x | 0 | false |

Four workers saved 733.2 seconds (12 minutes 13.2 seconds) versus serial and
completed the full executable corpus in 7 minutes 41.3 seconds. Eight workers
were slower and used more memory on this four-core/eight-thread host, so the
default remains four.

The memory gates passed:

- Four workers: 456.164 MiB, below 1.25 GiB and below 3.5x serial.
- Eight workers: 682.332 MiB, below 2 GiB and below 6x serial.

The predeclared speedup gates did not pass:

- Four workers: 2.589x, below the required 3.0x.
- Eight workers: 2.489x, below the required 2.5x.

No rounding or alternate corpus is used to promote those results. The practical
speed improvement is retained, while performance promotion remains `HOLD`.

## Single-formula latency

The serial receipt contained 356 documents parsed as exactly one formula and 12
documents parsed as multiple formulas.

- Single-formula median: 2.6 seconds
- Single-formula p95: 4.3 seconds
- Single-formula p99: 5.7 seconds
- Single-formula maximum: 10.3 seconds
- First discovered fresh subprocess in the measured serial run: 2.3 seconds

The warm single-formula p95 gate of at most 5 seconds passed. The 2.3-second
fresh-subprocess value is a cold-process proxy, not a reboot-and-cold-filesystem
measurement; a strict machine-cold claim is therefore not made.

## Determinism finding and repair

The first cross-worker comparison found 14–18 scientific-hash mismatches. An
exhaustive path comparison showed that every mismatch was only the order of the
set-valued `edge_cases.data.missing_classes` list; authority hashes, statuses,
numeric scientific values, and all other scientific paths were identical.

`future_modules/edge_cases.py` now sorts that list before return. Re-normalizing
all four immutable benchmark artifact sets by that declared set semantics left
zero residual files and zero residual paths. Fresh final-source runs over the
first 20 formulas, using different `PYTHONHASHSEED` values and one versus four
workers, then produced 20/20 identical scientific hashes, authority hashes, and
statuses with zero errors and zero drift.

The full four-way benchmark was not repeated after this order-only repair. The
timing values above remain useful performance evidence, but the unmet speedup
threshold already prevents performance promotion.
