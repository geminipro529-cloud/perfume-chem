# Build B1 Canonical Source and Provenance Registry Design

**Status:** Approved for implementation by the controlling
`SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md` and the user's standing instruction
to execute through Build D without additional approval pauses.

**Scope:** Build B, Phase B1 only. This design does not implement B2 property
observations, B3 threshold authority, B4 rule compilation, later Build B
backfill/API work, or any Build C/D behavior.

## Decision

Add a focused, append-only canonical source registry to the existing laboratory
SQLAlchemy database. Keep the legacy `LabEvidenceRecord` unchanged as a
compatibility record; it must not be treated as a canonical source version or
silently promoted.

Three approaches were considered:

1. **New canonical source module and tables (selected).** This preserves source
   versions, extraction context, state history, and source independence without
   overloading the legacy evidence row.
2. **Extend `LabEvidenceRecord`.** Rejected because one mutable-looking row
   cannot safely represent stable document identity, multiple versions,
   multiple extraction records, derivation links, and append-only workflow
   transitions.
3. **Use an engine-only JSON registry.** Rejected because it would create a
   parallel truth store outside the canonical database and its constraints.

## Canonical Data Model

Create `backend/app/models/lab_sources.py` with four append-only tables.

### `lab_source_document_versions`

Each row is one immutable version of a stable source:

- inherited row `id` and UTC `created_at`;
- `source_id`, `version_number`, `schema_version`;
- one of the 18 required `source_type` values from the master prompt;
- `title`, `authors_json`, `issuing_organization`;
- `container_title`, `publisher_or_authority`;
- identifiers in `identifiers_json` for DOI, PMID, standards, regulations,
  supplier documents, or stable accessions;
- publication, revision, effective, and retrieval dates;
- `edition_or_amendment`, `language`;
- `default_locator_json`, `original_unit`, `original_terminology`;
- `artifact_sha256`, `license_or_reuse_restriction`;
- repository-relative `preserved_artifact_path` only when lawful;
- `reviewer_pseudonym`, `review_state`;
- `supersedes_version_id`, `parent_record_sha256`, and `record_sha256`;
- nonblank `independence_group`.

Database checks constrain type, review state, positive version number, and
64-character digests. `(source_id, version_number)` and `record_sha256` are
unique. A source revision must name the latest version as its parent and must
preserve `source_id`.

### `lab_source_derivation_links`

Each row links a child source version to an upstream source version with one
explicit relation: `DERIVED_FROM`, `REPRODUCES`, `CITES`, or
`INCORPORATES`. Self-links, duplicates, and cycles are rejected. Several
documents in one `independence_group` remain one independent evidence lineage;
link count never becomes confidence by itself.

### `lab_source_extraction_records`

Each immutable extraction records:

- source version;
- exact locator and table/PDF structure in `locator_json` and
  `structure_context_json`;
- original wording and original value;
- parsed value and normalization/conversion;
- parser or model version;
- reviewer pseudonym;
- uncertainty and ambiguity;
- optional output observation ID reserved for the B2 canonical observation;
- input, output, and record SHA-256 digests.

The record must retain row, column, heading, and footnote context whenever those
features exist. An extraction with no output observation remains non-authority.
B2 may add the observation table and stronger linkage, but B1 does not create a
parallel placeholder observation table.

### `lab_evidence_workflow_events`

Workflow transitions are events, not updates. Each event identifies a source
version or extraction record, has a monotonically increasing sequence,
`from_state`, `to_state`, reviewer, scoped-use metadata, reason, and content
digest. Allowed states are exactly:

`STAGED`, `PARSED`, `IDENTITY_RESOLVED`, `UNIT_NORMALIZED`,
`CONDITION_NORMALIZED`, `CONFLICT_CHECKED`, `HUMAN_REVIEWED`,
`ACCEPTED_FOR_SCOPED_USE`, `REJECTED`, and `SUPERSEDED`.

Normal progression is ordered. Any nonterminal state may transition to
`REJECTED`; an accepted record may transition only to `SUPERSEDED`. Acceptance
requires a human reviewer, nonempty scope, exact locator, source and extraction
digests, and an output observation ID. A staged, parsed, or AI-extracted record
therefore cannot become runtime-authoritative automatically.

## Service and Repository Boundaries

Add `LabSourceRepositoryMixin` for deterministic reads only:

- source version lookup and latest-version lookup;
- parent/child derivation traversal;
- extraction lookup by source or output observation;
- ordered workflow events and effective state.

Add `LabSourceServiceMixin` to `LabService` for all writes:

- register or revise a source document;
- add a derivation link after cycle and identity checks;
- create an extraction record;
- append a validated workflow transition;
- reconstruct a deterministic source-to-extraction-to-observation derivation.

Input dataclasses normalize strings, dates, JSON copies, digests, and
repository-relative artifact paths. Stable JSON hashing covers all
authority-bearing fields. The service owns transactions; repositories do not
commit.

## Data Flow and Authority

```text
lawful source artifact/metadata
  -> immutable SourceDocument version (STAGED)
  -> immutable ExtractionRecord (STAGED)
  -> ordered workflow events
  -> B2 output observation ID
  -> ACCEPTED_FOR_SCOPED_USE with explicit scope
```

The reconstruction result includes every source version, derivation edge,
extraction locator, state event, digest, uncertainty, and output observation ID.
It does not emit a reliability score and does not grant any scientific claim.
Claim-specific authority remains B7.

## Migration and Compatibility

Add linear Alembic revision `20260730_0005`, down-revision
`20260730_0004`. It creates the four tables, constraints, indexes, and SQLite
append-only update/delete triggers. It performs no data backfill and changes no
legacy table or production scientific output.

Existing source locators, OAV results, headspace outputs, formula fixtures,
knowledge rules, and `LabEvidenceRecord` consumers remain byte-for-byte
compatible. B1 tests operate on temporary databases or verified copies; the
canonical database is restored and hash-checked after broader verification.

## Error Handling

Fail closed with stable source-authority error codes for:

- invalid type, state, digest, date, or artifact path;
- missing or nonlatest source parent;
- duplicate source version or record hash;
- self, duplicate, or cyclic derivation;
- skipped or terminal workflow transition;
- acceptance without human review, scope, locator, output observation, or
  required digests;
- reconstruction requests with no complete path.

No exception message includes environment values, document contents, or
credentials.

## Verification

TDD coverage must prove:

- all required source types and workflow states are constrained;
- versions are immutable and hash-chained;
- extraction preserves locator/row/column/footnote context;
- staged/parsed/AI-derived records are non-authoritative;
- illegal transitions, cycles, and false independence fail closed;
- accepted synthetic observations reconstruct complete derivations;
- migration upgrades empty and representative A5 databases, installs
  append-only guards, downgrades, and re-upgrades;
- no backfill occurs and legacy tables/fixture hashes remain unchanged.

The B1 exit gate passes only when every migrated high-impact value has a
complete reconstructable derivation. B1 intentionally migrates zero
high-impact values, while tests prove the complete reconstruction contract for
records created through the canonical service.
