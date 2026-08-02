# Build C7 lot-aware natural-material gate

Decision: **PENDING_EXACT_COMMIT_REPLAY**

The C7 implementation `ce78c450b6eeebe06180ae7e46030bff6da41747` has passed the local, mutation,
DeepLuna Fast, Sol-reconciliation, scope, archive, protected-state, and
log-hygiene gates. C8 remains closed until this evidence is committed and the
same matrix passes against that exact evidence commit.

## Implemented authority

- Immutable lot identity covers botanical, chemotype or variety, plant part,
  origin, harvest or production date, extraction and processing, supplier
  product and lot, receipt/opening, storage, oxidation/stability, source
  documents, analytical runs, and authenticity state.
- All nine constituent bases remain explicit. Normalized area percent is not
  concentration and is never promoted by this contract.
- Exact-lot quantified, exact-lot relative, supplier batch, specific
  literature proxy, generic proxy, and unknown precedence is fail-closed.
- Unknown peaks, coelution, unresolved groups, unidentified GC-O events,
  below-quantitation items, and unassigned mass or area remain visible.
- Olfactory/headspace, regulatory/allergen, and identity/authenticity
  projections are separate and basis-preserving.
- Aging snapshots version state without changing lot identity.

## Executable evidence

- C7 focused: 49 passed.
- C6/C5/C4/C3/C2/C1/C0 compatibility: 53 / 38 / 41 / 105 / 79 / 96 / 24 passed.
- Complete root suite: 1,583 passed.
- Dependency invariant, pip check, Ruff check/format, basedpyright, and mypy: passed.
- Four mutations were killed and restored byte-for-byte; source SHA-256 returned
  to `7e5e7774b8952f84af70b6f6a758573346e05ddd9d41c5e89e40b08929f8d29d`.
- Scope is exactly seven C7 paths with no production, database, migration,
  scientific-artifact, or legacy-natural path.
- The 118,324,736-byte path-preserving archive reverified with
  all 429 pre-existing dirty/untracked files
  preserved and zero mismatches.
- Protected database/WAL/SHM hashes and immutable quick checks are unchanged.
- All 92 captured log files are UTF-8, ANSI-free,
  and free of credential-shaped matches; stdout/stderr are separate.

## DeepLuna Fast and Sol reconciliation

Fresh exact-project health was `READY`. Job `DS-396c637bd50078cadd3e2d1c8ed61cde` completed
PASS/POSITIVE/COMPLETE with one DeepInfra Priority Flash call, `NO_LUNA`, no
negative findings, no scope deviation, and no Luna/GLM/Codex fallback. Sol
independently reproduced 34 gate-bearing tests. Postflight reservations are
zero. Provider findings are advisory only.

## Current boundary

C7 is a software authority contract; no actual natural-lot dataset was added or
validated. C5 empirical status remains `BLOCKED_PENDING_DATA`. C8 is closed
until the exact evidence-commit replay and final Sol decision pass.
