# Build B2 Property Authority Gate

Decision: **PASS**

Implementation authority:

- `aa91cda113931e85e318227dc9816bc091ed614d` — initial B2 property
  observation, conflict, assertion, repository, service, migration, and tests.
- `bdf839982fb4255488895bc091f16ad53bac8714` — Sol's independent
  gate fixes for identity-digest constraints, exact locator linkage,
  no-difference conflicts, assertion/conflict scope consistency, and explicit
  model/none selection behavior.

This gate covers Build B Phase B2 only. It does not implement contextual
threshold or OAV policy (B3), rule compilation (B4), analytical or regulatory
expansion (B5-B6), claim sufficiency (B7), decision-value backfill (B8), or
API/UI exposure (B9).

## Implemented canonical contract

- Five append-only canonical tables store typed property observations,
  explicit conflict sets and members, and versioned selected assertions with
  one decision and rationale for every candidate.
- Identity scope preserves chemical entity, stereoisomer/mixture, trade
  grade, supplier product, supplier lot, stock solution, physical dose, and
  natural material. Natural material requires all ten frozen identity
  dimensions; an explicit unknown value is permitted, but omission is not.
- Numeric, categorical, interval, distribution, and censored values are
  mutually exclusive at service and database boundaries.
  `NOT_DETECTED` has no numeric value and is never converted to zero.
- Observation creation requires the exact B1 source, extraction,
  reserved observation ID, locator, and accepted workflow scope.
- Conflicts require two or more unique observations and at least one visible
  difference. Typed values, conditions, methods, units, identities, and source
  independence remain visible; the service performs no averaging.
- Selected assertions are retrieved by explicit ID. There is no latest-value
  repository or service method. Observation, nonempty model, and explicit-none
  selection shapes are independently validated.
- An assertion linked to a conflict must match the conflict's identity digest,
  property, requested conditions, and complete member set. An unresolved
  blocking conflict must use `WITHHELD_CONFLICT`.
- Legacy `lab_material_properties` rows remain separate and append-only. The
  migration labels them `LEGACY_HEURISTIC` with an explicit reason and creates
  zero canonical B2 observations.

## Fresh verification

All commands ran non-interactively under supported Python 3.11.15, with ANSI
disabled, explicit timeouts, and separate stdout/stderr logs under
`docs/verification/b2/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr SHA-256 |
|---|---:|---|---|
| B1+B2+compatibility pytest | 73 passed in 73.65 s | `E98C9E01...1427CFC` | empty-file SHA |
| Ruff, exact B2 paths | all checks passed | `AF352A86...D2D9AF` | empty-file SHA |
| Mypy, three B2 modules | no issues | `F6AF9A42...8259C` | empty-file SHA |
| DeepLuna Fast post-fix delta audit | PASS | `D049F976...A3C70C` | empty-file SHA |

The full hashes, exact command strings, and paths are in
`property_authority_gate.json`.

The broader mypy import graph still reports four pre-existing errors in
`engine/calibration/store.py:83-86`. That diagnostic is preserved separately
and is not a B2 failure; scoped B2 typing is clean.

## Independent review and DeepLuna boundary

The first Fast-only audit returned PASS but omitted required file/line
citations. Sol did not accept it as authority and independently found five
gate gaps: missing identity-digest length constraints, missing extraction
locator equality, acceptance of no-difference conflicts, missing
assertion/conflict request matching, and an empty-model path. RED tests
reproduced all five, and the focused fixes are commit `bdf8399`.

After the fixes, the authoritative suite passed 73/73 and one fresh,
Fast-only delta audit (`DS-7daff23d16def41f6c1a46eaf585997b`) returned
terminal PASS with no blocking findings. That packet again omitted the
requested detailed citations, so it remains supplemental. Sol independently
reproduced every corrected invariant using executable tests and direct source,
model, and migration comparison.

No Codex subagents, Luna fallback, or non-Fast provider route was used.

## B2 exit decision

The master exit gate is:

> Every migrated runtime property is traceable to an observation and selected
> assertion, or is explicitly labeled as legacy heuristic.

The B2 migration promotes zero runtime properties. Every pre-B2 scalar row
receives the nonnullable `LEGACY_HEURISTIC` label and explicit reason.
Representative migration testing proves one legacy row is preserved and
labeled while all five canonical B2 tables remain empty. Synthetic temporary
records prove exact B1 linkage, typed values, conflicts, candidate decisions,
assertion reconstruction, and authority withholding. Therefore the gate
passes without claiming that any legacy property is scientifically true.

## Protected state and recovery

- `perfume_chem.db` remains zero bytes with SHA-256
  `E3B0C442...B855`.
- `data/perfumery_kb.db` remains 2,084,864 bytes with SHA-256
  `5A779F9D...3FE1`; SQLite integrity is `ok`.
- The pre-promotion path-preserving recovery archive is
  `outputs/b2-prepromotion-recovery/canonical-b2-targets-prepromotion.zip`
  in the Codex evidence workspace, SHA-256
  `D31ECAB5...A368C`. It was extracted into a separate directory and every
  restored file matched its source hash.
- The A0 full recovery package remains preserved.
- Before the B2 report commit, the existing worktree still had 105 tracked
  dirty paths, 535 untracked files, and zero staged entries. Only exact B2
  paths were committed.

## Limitations and claim boundary

- B2 ingests and promotes no real literature property values.
- Real legacy-property truth remains unknown; the explicit legacy label is a
  quarantine state, not evidence.
- Contextual threshold and OAV applicability remain B3.
- No production API/UI consumer is connected until B9.
- The DeepLuna result packets did not satisfy the requested citation detail;
  local deterministic evidence remains controlling.
- Scientific release remains **BLOCKED**.

B3 may begin only under its own RED tests and exit gate. This B2 PASS must not
be interpreted as scientific truth, claim sufficiency, or release authority.
