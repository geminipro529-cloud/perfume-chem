# Build C6 dynamic-release gate

Decision: **PASS**

The C6 implementation `5b51ab31ddc28b48efa78944b314919f226262b2` and evidence
commit `f45239862276b077833a18b5a8e81d5b76021037` passed the local, mutation, DeepLuna Fast,
Sol-reconciliation, and exact-commit replay gates. C7 is open.

## Implemented authority

- Conservative condensed, gas, sorbed, and explicit-sink compartments.
- Bounded `1 - exp(-k * dt)` hazards with per-component closure checks.
- Sealed-vial and finite-film geometry kept separate.
- Solvent loss updates later film composition and release rates.
- Lower, nominal, and upper deterministic sensitivity scenarios; the envelope
  is not a confidence or credible interval.
- Exact C2 matrix/environment, C3 selector/input-reference, component, and
  substrate-kind binding with abstention before invalid computation.

Permitted labels are only `PREDICTED_HEADSPACE_TRAJECTORY`,
`PREDICTED_RELEASE_TRAJECTORY`, and `ESTIMATED_PHYSICAL_PERSISTENCE`.
The model is `SIMULATION_ONLY_UNCALIBRATED` and `UNVALIDATED`; it does not
authorize longevity, sillage, projection, perceived intensity, temporal
attributes, measured performance, or empirical promotion.

## Executable evidence

- C6 focused: 53 passed.
- C5/C4/C3/C2/C1/C0 compatibility: 38 / 41 / 105 / 79 / 96 / 24 passed.
- Complete root suite: 1,534 passed.
- Dependency invariant and `pip check`: passed.
- Ruff check/format, basedpyright, and mypy: passed.
- Four mutations were killed and each restored test passed; source SHA-256
  returned to `d9603eb2bf426379aad46757811e473267d289ffda8f0cf12c5867b5994b4b2f`.
- Scope is exactly seven C6 paths with no production, database, migration,
  scientific-artifact, or legacy-dynamic path.
- The 118,322,688-byte path-preserving archive
  reverified with all 429 pre-existing dirty/untracked files preserved and zero
  mismatches.
- Protected database/WAL/SHM hashes and immutable quick checks are unchanged.
- All 90 original
  captured log files are UTF-8, ANSI-free, and free of credential-shaped
  matches; stdout/stderr are separate.
- The exact evidence commit replay passed all 23 bounded
  jobs with zero failures, timeouts, stderr bytes, ANSI escapes, or
  credential-shaped matches.

## DeepLuna Fast and Sol reconciliation

Fresh exact-project health was `READY`. Job `DS-377cfe1ca9f9da6474cf225a2048fb27`
completed PASS/POSITIVE with one DeepInfra Priority Flash call, `NO_LUNA`, no
negative findings, no scope deviation, and no Luna/GLM/Codex fallback. Sol
independently reproduced the source findings and reran 18 gate-bearing tests.
Postflight reservations are zero.

## Current boundary

C6's conservative dynamic-release implementation and exact evidence replay are
green, and C7 is open. C5 empirical status remains `BLOCKED_PENDING_DATA`:
there are no actual instrument data, empirical metrics, or promoted empirical
claims. This decision opens only the next software phase.
