# Build B1 Source Provenance Gate

Decision: **PASS**

Implementation authority: commit
`448f69cb9cf23e9e59f7960e77b378ae8e09725a` on
`codex/add-inventory-materials`. Current verification began at Build B0 seal
`59637597706569360220e0354716ceeb4e4837ca`.

This gate covers Build B Phase B1 only. It does not claim that any migrated
scientific value is true, that a claim may be released, or that later Build B
authority work is complete.

## Implemented canonical contract

- 18 explicit source types are stored as immutable
  `lab_source_document_versions`.
- Source revisions are stable-ID/version pairs with parent hashes,
  supersession links, exact identifiers/locators, content digests, review
  metadata, independence groups, and lawful repository-relative artifact
  paths.
- Extractions preserve original wording/value, parsed value,
  normalization/conversion, parser/model version, uncertainty, ambiguity,
  exact locator, table/PDF structure, input/output hashes, and the reserved B2
  observation ID.
- Workflow changes are append-only events over the exact ten master states.
  Staged, parsed, and AI-generated records are non-authoritative.
- Explicit derivation links reject self-links, duplicates, and cycles.
  Reconstruction returns deterministic source, extraction, workflow, digest,
  and independence-group evidence without inventing a reliability score.
- B1 owns revision `20260730_0005`; the current linear repository head is
  `20260731_0012`. The B1 migration creates four append-only tables, performs no
  backfill, preserves representative A5 schema/rows, and
  downgrades/re-upgrades cleanly in disposable databases.

## Fresh verification

All commands ran non-interactively with ANSI disabled and explicit tool
timeouts. Stdout and stderr are preserved separately under
`docs/verification/b1/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr SHA-256 |
|---|---:|---|---|
| B1 plus compatibility pytest | 45 passed in 48.85 s | `277B5CE9...D0AB7` | empty-file SHA |
| Ruff | all checks passed | `AF352A86...D2D9AF` | empty-file SHA |
| Mypy, three B1 modules | no issues | `F6AF9A42...8259C` | empty-file SHA |

The full hashes and exact paths are in
`source_provenance_gate.json`.

Compatibility coverage includes the current B1 schema/service/migration tests,
general laboratory migration behavior, and backup/restore. Historical counts
were not reused; the live five-file selection produced the 45-test result above.

## B1 exit decision

The master exit gate is:

> The project can reconstruct the complete source-to-observation derivation
> for every migrated high-impact value.

B1 intentionally migrated **zero** high-impact values. The migration test
proves all four B1 tables start empty, and the migration contains no data
insertion or backfill. Synthetic accepted records prove the complete
source-to-extraction-to-observation reconstruction contract, including exact
scope and independence collapse. Therefore the gate passes for the empty
migrated set without promoting any legacy value.

## Preserved authority and state

- No `engine/` path changed from the B0 implementation point through this B1
  implementation.
- No production scientific consumer is connected to B1 acceptance.
- `LabEvidenceRecord` remains a compatibility record and is not promoted.
- Canonical `perfume_chem.db` is a valid 12,288-byte SQLite file with SHA-256
  `02B64BE8...A0DA5`, `quick_check=ok`, and zero Alembic rows.
- `data/perfumery_kb.db` remains 2,084,864 bytes with SHA-256
  `5A779F9D...3FE1`; a byte-identical copy reports SQLite integrity `ok`.
- Existing work remains preserved: 105 tracked dirty paths, 1,122 untracked
  files, and zero staged entries before this report commit.

The previous reports and six logs were archived and restore-verified at
`outputs/b1-authoritative-recovery/20260802T061536/` and
`outputs/b1-log-recovery/20260802T061609/` before replacement.

## Limitations and claim boundary

- `output_observation_id` is a reserved immutable identifier until B2 creates
  the canonical observation model; B1 did not create a parallel placeholder.
- Mypy was scoped with `--follow-imports=skip` because unrelated pre-existing
  `engine/calibration/store.py` typing failures are outside B1.
- No literature assertion was newly ingested, verified, selected, or promoted.
- Claim-specific authority remains B7.
- Scientific release remains **BLOCKED**.

DeepLuna Fast review `DS-1e8e104e048d82ab80098c5b5ec7d403` returned
`PASS` / `POSITIVE` / `ACCEPTED`, no negative findings, and no scope deviation.
It identified report staleness only; Sol accepted that conclusion after the
current 45-test, Ruff, mypy, migration-head, hash, and database checks passed.

B2 must not infer scientific authority from this B1 PASS. It may proceed only
under its own observation-first exit gate.
