# Build C8 headspace OAV and interaction-authority gate

Decision: **PENDING_EXACT_COMMIT_REPLAY**

Implementation `511504f1fd3e1c195a909dbab31836398d608dd5` passed the local, mutation, DeepLuna
Fast, Sol-reconciliation, scope, archive, protected-state, and log-hygiene
gates. C9 remains closed until this evidence is committed and the same matrix
passes against that exact evidence commit.

## Implemented authority

- OAV is computed only from an admissible measured or in-domain predicted gas
  concentration and a context-compatible, unit-matched detection threshold
  with bounded uncertainty.
- Failed preconditions produce answerless abstention. OAV is screening, not
  exact intensity, percent contribution, similarity, or preference.
- Interaction records preserve identities, bounded concentrations, context,
  method, assessor population, source, uncertainty, and applicable ranges.
- Observation-only and uncalibrated-generic records cannot carry numerical
  effects. Authorized calibrated effects are exposed but never applied by C8.
- The exact eight-stage sensomics sequence gates candidate prioritization and
  tested-context recombination or material-effect claims.

## Executable evidence

- C8 focused: 78 passed.
- C7/C6/C5/C4/C3/C2/C1/C0 compatibility: 49 / 53 / 38 / 41 / 105 / 79 / 96 / 24 passed.
- Complete root suite: 1,661 passed.
- Dependency isolation, inventory verifier, pip check, Ruff check/format,
  basedpyright, and mypy: passed.
- Four mutations were killed and restored byte-for-byte; source SHA-256 returned
  to `8cab711492f9cff7cd7c53cae8bc176fc045e35cabc2e6bd80c6bcb8dcfe42e1`.
- Scope is exactly seven C8 paths with no production, database, migration,
  scientific-artifact, or legacy OAV/interaction path.
- The 118,328,832-byte path-preserving archive reverified with
  all 429 pre-existing dirty/untracked files
  preserved and zero mismatches.
- Protected database/WAL/SHM hashes and immutable quick checks are unchanged.
- All 127 captured log files are UTF-8, ANSI-free,
  and free of credential-shaped matches; stdout/stderr are separate.

## DeepLuna Fast and Sol reconciliation

Fresh exact-project health was `READY`. Job
`DS-d54912b0cee881229783207149823ebe` completed PASS/POSITIVE with one
DeepInfra Priority Flash call, `NO_LUNA`, no negative findings, and no fallback.
Sol independently reproduced every worker-positive finding. Postflight queue,
active lanes, and reservations are zero. Provider findings are advisory only.

## Current boundary

C8 is a software authority contract. It validates no threshold table,
interaction dataset, sensory study, production formula, exact intensity,
longevity, sillage, or preference claim. C5 empirical status remains
`BLOCKED_PENDING_DATA`. C9 is closed until exact-commit replay and final Sol
decision pass.
