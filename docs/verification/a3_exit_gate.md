# Build A Phase A3 exit gate

Date: 2026-07-30

Status: PASS for the local software gate. This does not grant scientific
release authority; held-out sensory validation remains absent.

## Implemented boundary

- `engine/canonical_serialization.py` is the closed, typed serialization
  boundary. Only explicitly registered dataclasses and enums are restored.
  Tagged UUIDs, dates, aware datetimes, exact decimals, tuples, sets,
  quantities, concentration bases, uncertainty records, schema versions, and
  namespaced extensions round-trip without dynamic imports.
- `backend/app/services/lab_export.py` exposes
  `CURRENT_WRITE_REVISION = lab-export-v4` and migrates v1 -> v2 -> v3 -> v4
  explicitly. Unknown future revisions, unknown source tables, and unknown
  top-level fields fail closed. Namespaced extension payloads are preserved.
- `engine/quantities.py` separates raw, technical-active, active, carrier,
  ethanol, water, other-solvent, and unallocated mass; raw, active, carrier,
  and solvent volume; density applicability; uncertainty; measurement
  resolution; concentration fraction; and concentration basis. Unsafe
  conversions return the required stable `IncomparabilityReason`.
- `engine/calibration/hashing.py` has tagged exact canonical values and a
  versioned SHA-256 record containing schema, stable IDs, canonical units,
  ordered line IDs, parent hash, source digests, algorithm ID, transformation
  version, and canonical payload hash. Filesystem paths and naive datetimes are
  rejected.
- `engine/provenance.py` represents entities, activities, agents, generation,
  derivation, transformations, software/model versions, parameters,
  timestamps, evidence class, uncertainty, human review, and AI proposal
  review metadata in a W3C-PROV-shaped payload.
- New formula artifacts bind canonical record IDs/versions/content hashes,
  renderer version, analysis-input hash, generation timestamp, and repository
  commit. Validation re-reads and checks the binding.
- `scripts/rebind_formula_artifact.py` refuses paths outside the repository,
  ambiguous multi-formula files, unstaged changes, and unacknowledged staged
  changes; it prints a semantic diff and delegates hash generation and
  post-write verification to the canonical release pipeline.

## Test evidence

- Focused A3 root tests: 40 passed.
- Focused export migration tests: 3 passed.
- Full backend suite: 275 passed.
- First full root run: 1,011 passed and one shard-manifest failure.
- Defect correction: all five new root test modules were added exactly once to
  the canonical shard manifest.
- Full root rerun: 1,012 passed.
- A3 canonical modules were added to the repository-owned Ruff and MyPy
  surfaces. The focused verifier rerun passed Ruff and MyPy for 31 engine
  source files.
- Artifact verifier: exit 0, status `WARN`, 452 `NONE`, 14 explicitly
  `QUARANTINED`, 49 `UNBOUND_LEGACY`, and zero blocking unquarantined `STALE`
  or `TAMPERED` artifacts.
- Golden fixture lock remained
  `0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec`.

## Canonical verifier

The full verifier report at
`verification_runs/a3-project-verification.json` recorded:

- 19 required checks passed;
- zero failures;
- optional Docker build and smoke checks skipped because Docker was not
  requested;
- completion gate `PASS_WITH_SKIPS`;
- report SHA-256
  `4169b406b4c53412857c241b25c3cf741f05e413bf502d5f721134bff520ad48`.

The verifier manifest was then expanded to lint and type-check the new A3
modules. Its exact focused rerun passed, followed by the full exact-state
verifier result and report hash recorded above.

## Protected database state

After the tests and verifier, `data/perfumery_kb.db` was restored from the
previously verified path-preserving recovery candidate:

- SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- SQLite `PRAGMA integrity_check`: `ok`.

The protected canonical `perfume_chem.db` remained zero bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## DeepLuna audit note

Two attempted A3 audit packets were rejected locally before provider
execution because their packed evidence exceeded the declared input ceilings.
They are not acceptance evidence and were not retried by increasing provider
scope. A3 acceptance rests on repository code, tests, artifact validation,
database restoration, and the canonical verifier.

## Exit decision

All A3 exit conditions pass for the local software boundary:

- canonical records round-trip with correct runtime types;
- every supported old export migrates to the current writer;
- unsafe quantity conversions fail with structured reasons;
- canonical hash bytes and metadata are deterministic;
- provenance reconstructs derivation and review;
- artifact validation has no blocking unquarantined stale/tampered record;
- the repository-owned verifier passes.

Scientific release remains blocked by missing held-out sensory validation.
