# Verification repair result — 7 October 2026

The reproduced software and verification defects are repaired. This is a
software-repair acceptance record, not perfume-science, physical-build, safety,
commercial-release or merge acceptance. The original failed full report remains
at `output/subtype_v5_full_20261007.json`; it has not been overwritten.

## Runtime changes

- Optional OpenTelemetry exporters load only after explicit tracing setup.
  Importing ordinary engine functionality no longer imports the incompatible
  optional protobuf exporter. Explicit exporter failures still fail visibly;
  live OTLP export on Python 3.14 was not certified.
- Root tests have an explicit package identity. Historical backend inventory
  fixtures reconstruct the exact original bytes rather than replacing pins.
- Advisory arithmetic rejects missing/invalid/conflicting positive-dose stock
  strengths. Explicit neat solids remain solids; no mass-to-volume conversion
  or unknown physical property is invented.
- The scientific-ingestion CLI supports governed local staging, related-source
  verification, dry-run and structured rejection. No implicit download or
  canonical evidence admission was added.
- The native complexity admission adapter reads actual native receipt/status
  fields and independently verifies preflight binding. Its unsupported
  measured-delivered-air OAV certification remains ABSTAINED.
- The original additive v2 complexity overlay is preserved; a separate v3
  census binds current bytes without promoting or reactivating retired models.
- The research index has a separately versioned v2 successor for eight
  independently verified LF/CRLF-only differences. Original v1 bytes, titles,
  search terms, order, review status and authority are unchanged. Both index
  versions and referenced source bytes participate in durable job fingerprints.
  Semantic edits and parent drift still withhold retrieval.
- The existing OpenCode launcher path now points to its actual project launcher.
  No provider, launcher or delegated model was invoked.
- The full-backend verification wrapper budget is 1,800 seconds because a
  reproduced complete run exceeded its old 1,200-second budget. Normal formula,
  mixer and engine-job timeouts were not increased.

## Fresh verification

| Check | Outcome |
|---|---|
| Canonical root shards and additional regression batches | 5,223 passed; zero failures/errors; one opt-in timing skip |
| Focused final repair regression | 364 passed; overlaps the root totals |
| Complete backend suite, before the final research-index successor | 892 passed |
| Final backend changed-surface unit/integration suite | 62 passed in 43.86 seconds |
| Backend Ruff and mypy | Passed; 153 source files type-checked |
| Scoped root Ruff and mypy | Passed; five repaired source files type-checked |
| Final quick project verifier | 10 passed; zero failures/skips; partial scope |
| Git diff check | Passed |

Root reports were generated as separate frozen-source batches, not as a newly
successful canonical full-verifier wrapper run. Their filenames and SHA-256
values are recorded in `VERIFICATION_REPAIR_RESULT_20261007.json`.
The timing skip is `test_paired_formulation_performance`, which requires
explicit performance-acceptance opt-in; speed work was excluded from this repair.

The sandboxed focused backend rerun stalled at isolated child execution. It was
not accepted as green. After verifying its exact PID, command and creation time,
only that test process was stopped; application services were untouched and
failed scratch was retained. The identical complete 62-test subset then passed
outside the sandbox, including isolated execution, hard timeout, worker-loss,
idempotency, cancellation, result chains and real durable-job API routes.

## Historical truth and residual limits

Nine exact historical source versions could not be recovered from current
files, scoped Git history or searched archives. Their original receipts/hashes
remain unchanged. The separate replay review records
`HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE`; this is not a substitute historical
replay or current-runtime acceptance. Tests independently exercise current drift,
stock holds and authority ceilings.

Source-bound natural-model drift remains a HOLD rather than a new calibration.
The research census indexes 128 references; it is not full-text review, complete
perfume coverage, empirical admission or consumer/sensory evidence.
Incomplete current bottle/lot/preparation receipts remain non-executable rather
than silently inheriting historic physical readiness. Ordinary advisory scent
research is not a physical execution claim.

No live inventory entry or formula dose changed. Some sealed archive/formula
files had newline bytes restored only after independent agreement with their
unchanged original hash/ZIP/Git evidence; material names, doses and content were
not reformulated. Existing dirty work and the Orris Liquid compounding hold were
preserved. No Git reset, cleanup, commit, push or worktree deletion was performed.

Docker runtime smoke, new timing acceptance, full-engine legacy lint cleanup,
live OTLP export, empirical/sensory validation, physical compounding and release
readiness are not claimed. All perfume action-authority flags remain false.

## Evidence

- `output/verification_repair_quick_final_20261007.json`
- `output/verification_repair_backend_20261007.xml`
- `output/verification_repair_backend_jobs_accepted_20261007.xml`
- `output/verification_repair_remaining_final_20261007.xml`
- `data/governance/historical_source_replay_review_20261007.json`
- `VERIFICATION_REPAIR_RESULT_20261007.json` — exact source and report pins
