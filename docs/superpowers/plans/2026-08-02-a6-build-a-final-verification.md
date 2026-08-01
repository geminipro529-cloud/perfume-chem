# Build A Phase A6 final verification plan

Date: 2026-08-02

## Goal

Produce the authoritative Build A convergence evidence from baseline
`0fa0adff1533ffca1ad74e6e6904b1afc1b1d435` through the final Build A
checkpoint. Replace stale convergence reports only after an independent diff
review and a fresh full canonical verifier.

## Constraints

- Stop at the Build A boundary. Do not begin Build B in this run.
- Preserve every unrelated tracked and untracked path. Do not clean, reset,
  migrate the default database, regenerate release artifacts, or expose
  secrets.
- Archive and restore-verify every report that will be replaced.
- Use supported Python 3.11, non-PTY verification, disabled ANSI output,
  separate stdout/stderr capture, explicit timeouts, and machine-readable
  artifacts.
- DeepLuna Fast provides bounded independent review only after a fresh exact-
  project readiness check. Sol retains security, architecture, scientific,
  provenance, and final acceptance authority.

## Independent review

1. Enumerate every committed Build A path and inspect its diff from the A0
   baseline.
2. Search for duplicate persisted models, endpoint-owned transactions,
   direct/legacy write paths, shallow deserialization, and public API drift.
3. Inspect migration heads/history, all Build A migration contracts, changed
   tests, changed expected values, generated files, large files, and
   source/documentation consistency.
4. Scan only committed Build A diffs for high-confidence secret markers;
   never open ignored environment files or print environment values.
5. Map all A6 risk categories to executable tests and verifier checks.

## Verification and evidence

1. Run the complete canonical verifier from the current Build A tree and
   preserve stdout, stderr, report, timing, hashes, counts, skips, and database
   state.
2. Re-run concise architecture, write-path, migration, artifact, and API
   consistency checks where the canonical report needs independent support.
3. Write `canonical_convergence_report.md` and its JSON companion with baseline
   and final SHA, recovery proof, worktree state, changed files, migrations,
   architecture, original defect dispositions, verifier evidence, acceptance
   matrix, skips, limitations, deprecated paths, rollback, and exact release
   status.
4. Run one bounded exact-project Fast audit over the completed report and
   machine verifier, resolve any reproduced contradiction, then perform Sol's
   final review.
5. Check the exact diff and commit only the A6 plan and two convergence reports.

## Exit decision

Build A passes only if recovery remains proven, one canonical persisted truth
path exists, planning is canonical, typed serialization is complete, legacy
writes fail closed, target/inventory/build/bottle remain separate, physical
operations are atomic and replayable, critical claim gates fail closed,
artifacts are bound, every limitation is explicit, and the product remains
Laboratory Beta with scientific release blocked.
