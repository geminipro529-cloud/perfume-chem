# Build A Phase A3 exit gate

Date: 2026-08-02

Authoritative source baseline:
`f941ad8a41d2a6ff5c968753458d3fc0f0901197`.

Status: PASS for the local software gate. This gate does not grant scientific
release authority; held-out sensory validation remains absent.

## Reverification method

The 2026-07-30 report was treated as a historical lead and was independently
checked against the live tree. Its test counts, verifier hash, and root
database description were stale. Before replacement, the report was preserved
in the path-restorable archive
`a3_prereport_20260802_042150.tar`; archive SHA-256 is
`d10aa1ee0d4087f34f6e992ff8a2abe6b66b088b787d78f68ef876656d98bedb`.
An extracted copy matched the original SHA-256 exactly.

No production source, migration, database, or release artifact was changed by
this reverification.

## Implemented boundary

- `engine/canonical_serialization.py` restores only registered dataclasses and
  enums. UUIDs, dates, aware datetimes, exact decimals, tuples, sets,
  quantities, concentration bases, uncertainty records, schema versions, and
  namespaced extensions retain their runtime meaning.
- `backend/app/services/lab_export.py` writes `lab-export-v4` and migrates each
  supported v1, v2, and v3 packet explicitly. Unknown revisions, source
  tables, and unscoped top-level fields fail closed; namespaced extensions are
  preserved.
- `engine/quantities.py` keeps amount, unit, basis, density applicability,
  uncertainty, and measurement resolution explicit. Unsafe comparisons return
  a stable structured `IncomparabilityReason`.
- `engine/calibration/hashing.py` produces deterministic canonical bytes and a
  versioned SHA-256 record with stable identifiers, canonical units, ordered
  line identifiers, source digests, transformation metadata, and payload hash.
  Naive datetimes, non-finite floats, and filesystem paths are rejected.
- `engine/provenance.py` emits W3C-PROV-shaped entity, activity, agent,
  derivation, generation, software/model, evidence, uncertainty, human-review,
  and AI-proposal metadata.
- Formula artifacts bind canonical record identity and version, content and
  analysis-input hashes, renderer version, generation time, and repository
  commit. Rebinding remains constrained by repository path, formula ambiguity,
  staged-state acknowledgement, semantic diff, and post-write verification.

## Fresh focused evidence

- Six root A3 contract modules: 41 passed in 8.43 seconds.
- Root JUnit SHA-256:
  `45058b0380248442e051641fbb82fb27e1094f55e42255f31a46f1bd7466a515`.
- Root captured stdout SHA-256:
  `9e55928d97aa49d1f4b057b88a5a99e9c34ce72051b894a3b746dbf6597f3064`;
  captured stderr was empty.
- Backend export migration module: 3 passed.
- Backend JUnit SHA-256:
  `b56719f55769c60a00bfad6b7b8d049abf9fbf33481e663ce5ba8f69caf7673d`;
  captured stderr was empty.
- Artifact verifier exited successfully with status `WARN`: 452 `NONE`, 14
  explicitly `QUARANTINED`, 49 `UNBOUND_LEGACY`, and zero blocking `STALE` or
  `TAMPERED` files. Its captured JSON SHA-256 is
  `3e5eadb78c598d2c751ce8a7fa8919f3be26a2da7afc7cd5874c8f0ef6247e2d`;
  captured stderr was empty.

After the report and audit record were finalized, the same six root modules
again passed 41 tests; post-audit JUnit SHA-256 is
`52221fb7cff405f5d7a9eb68f46d8406a5d51875cd91ad6482c19deb7283d56b`.
The export migration module again passed all 3 tests under the supported
Python 3.11 verifier environment; post-audit JUnit SHA-256 is
`6a41c1948dc37f70e8f8811ef5aac66d4ca926371870cbbeea74c108be69161c`.

Two non-authoritative command attempts were diagnosed and excluded: the root
3.11 environment lacked `pytest_asyncio`, and the legacy Python 3.14 backend
environment could not load its mismatched `greenlet` extension. Neither
attempt reached an application assertion. The supported Python 3.11 backend
environment produced the passing result above.

## Canonical verifier

The final full exact-state verifier at
`verification_runs/project_verification.json` records 19 passed checks, zero
failures, zero omitted checks, and two optional Docker skips because Docker was
not requested. The completion gate is `PASS_WITH_SKIPS`; engine, backend, and
combined test counts are 1,095, 630, and 1,725. Report SHA-256 is
`52491a72415ba34881d13c212269325add6b183b56e74071f4f08e58ebb4e95a`.
The non-PTY run completed with exit code 0 in 687.8 seconds. Captured stdout
SHA-256 is
`a37efd7e9d01addbca940a62c123fbe3c2425282510fe483c7fa1c6307b9499a`;
captured stderr was empty.

## Protected database state

Both databases were inspected read-only after the focused runs:

- `data/perfumery_kb.db`: 2,084,864 bytes, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`,
  SQLite `PRAGMA quick_check` `ok`, and `user_version` 0.
- `perfume_chem.db`: 12,288 bytes, SHA-256
  `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`,
  SQLite `PRAGMA quick_check` `ok`, and `user_version` 0. It contains only an
  empty `alembic_version` table. The previous claim that this file was zero
  bytes is not current.

These observations do not promote either file or claim migration state. The
independent Alembic gate remains the repository migration command and its
single current head, not this local root file.

## DeepLuna Fast audit

A first audit packet was rejected locally because one requested evidence range
exceeded its file length. It reached no provider and is not acceptance
evidence.

After correcting the range, a new exact-project check returned `READY` for
`project_id=perfume-chem`, runtime `CANDIDATE_V2`, server 0.9.9, zero active or
queued work, zero open or unknown reservations, and provider calls enabled.
The bounded read-only Fast audit was job
`DS-197eebe79464962524c987486725810c` with route `FLASH`, fallback policy
`NO_LUNA`, one allowed provider call, and no cache hit. It returned:

- job status `PASS`;
- execution status `ACCEPTED`;
- evidence verdict `POSITIVE`;
- no negative findings, residual risks, scope deviation, architecture
  uncertainty, or scientific uncertainty;
- summary: all six A3 exit conditions are supported, with no contradiction or
  acceptance-blocking gap.

The app connector bound to the wrapper workspace was not used as acceptance
evidence. DeepLuna supplied bounded review evidence only; Sol made the final
gate decision from the repository state and reproduced local results.

After the current-state full verifier and report hash were recorded, final
Fast seal job `DS-21d71ea2d5da5960367b576dde89caa4` read this exit report and
the machine verifier report. It returned `PASS`, execution status `ACCEPTED`,
and evidence verdict `POSITIVE`, with no negative findings, residual risks,
scope deviation, contradiction, or acceptance-blocking gap. It confirmed that
all 19 required checks passed, the two Docker skips are optional, and the local
software, migration, database-observation, and scientific-release authority
boundaries remain distinct.

## Exit decision

The locally reproduced A3 evidence satisfies the software boundary:

- canonical records round-trip with correct runtime types;
- every supported old export migrates to the current writer;
- unsafe quantity operations fail with structured reasons;
- canonical hash bytes and derivation metadata are deterministic;
- provenance reconstructs derivation and review;
- artifact validation has no blocking unquarantined stale or tampered record;
- the repository-owned verifier passes.

A3 is accepted for the local software boundary. Scientific release remains
blocked by missing held-out sensory validation.
