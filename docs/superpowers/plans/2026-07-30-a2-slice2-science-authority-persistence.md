# A2 Slice 2 Science Authority Persistence Implementation Plan

> **Execution rule:** Sol is the sole head engineer and final approver. No
> Codex subagents are permitted. DeepLuna Fast may perform bounded read-only
> extraction, but architecture, scientific meaning, provenance, security,
> scope, and acceptance remain local Sol decisions.

**Goal:** Add append-oriented canonical persistence for analytical
methods/runs/results, dated regulatory assessments, and claim-specific
authority decisions without promoting the legacy in-memory analytical ledger,
the heuristic regulatory helper, or either legacy `AuthorityVector` class into
canonical truth.

**Architecture:** Extend the accepted `lab_*` SQLAlchemy/Alembic authority
with one focused science-authority model module. Compose query and command
mixins through the existing `LabRepository` and `LabService` transaction
owner. Extend deterministic export/import to an explicit v3 graph while
retaining v1 and v2 readers and the protected v1 endpoint default. Store
immutable records, hashes, evidence links, and attachment digests; never store
raw attachment bytes, secrets, averaged authority scores, inferred release
authority, or fabricated measurements.

**Tech stack:** Python 3.11, SQLAlchemy 2, Alembic, aiosqlite, pytest,
pytest-asyncio, Ruff, MyPy, SQLite.

---

Status: approved for autonomous execution by the user's standing A through D
authorization.

Starting implementation checkpoint:
`7e0dc59ef031301a19561f7d167fa863ad8b5c14`

Required predecessor gate: `A2_SLICE1_PASS`

DeepLuna bounded pattern extraction:
`DS-03d4ee6e30d9674454bc52d7089f2c0c` (`PASS`)

Protected preimplementation recovery package:
`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-slice1-preimplementation-recovery\perfume-chem-a0-20260729T194130Z`

## Entry evidence

Before this plan was written, Sol reconfirmed:

- recovery restoration verification is true;
- source changes during archive capture are zero;
- the authoritative branch is `codex/add-inventory-materials`;
- the starting commit is
  `7e0dc59ef031301a19561f7d167fa863ad8b5c14`;
- the existing dirty and untracked work remains present;
- `perfume_chem.db` remains zero bytes with SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- `data/perfumery_kb.db` has SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`.

No archive inventory containing sensitive path names may be printed or sent to
a provider.

## Scope boundary

This plan covers only approved A2 Slice 2:

1. versioned analytical method persistence;
2. analytical run, peak, QC, attachment-digest, and GC-olfactometry event
   persistence;
3. dated regulatory assessment and finding persistence;
4. claim-specific authority assessment and evidence-link persistence;
5. deterministic v3 export/import and migration-copy evidence.

This slice does not:

- adapt or write through the legacy engine analytical ledger;
- close legacy dual-write paths;
- edit or delete legacy tables;
- change `engine/safety/regulatory.py`;
- persist either legacy `AuthorityVector` representation;
- create source-document/property-observation authority required by Build B;
- add release decisions, sensory release, or human authorization;
- expose new API routes;
- migrate the zero-byte canonical `perfume_chem.db`;
- begin A2 Slice 3, A3, Build B, Build C, or Build D.

Passing this slice establishes only `A2_SLICE2_PASS`.

## Sol architecture decisions

### Canonical analytical boundary

Dedicated analytical tables are required. Generic `LabObservation` records do
not carry method version, instrument acquisition, chromatographic peak,
quantitation basis, QC, or attachment-digest contracts and therefore are not
used as a substitute.

### Regulatory boundary

`LabRestriction` remains the canonical source record for a restriction.
`LabRegulatoryAssessmentVersion` records a dated evaluation of a defined
subject against a named standard state. An assessment may link findings back
to restrictions, but it must not rewrite or silently supersede them.

Unknown, missing, stale, or conflicting regulatory authority is represented
explicitly. This slice must never interpret "not found" as unrestricted.

### Claim-authority boundary

Canonical claim authority is a claim-specific decision record with explicit
support, missing evidence, conflicts, permitted wording, forbidden wording,
and human-review state. The old floating-point `AuthorityVector` classes are
derived computations and are not persisted.

### Attachment boundary

Only attachment metadata, byte length, storage locator, and SHA-256 digest are
stored. The database and export packet contain no raw attachment bytes.

### Transaction boundary

`LabService` retains transaction ownership. Repositories issue queries and
flush records but do not commit, roll back, or perform scientific arithmetic.

## Locked file map

### Create

- `backend/app/models/lab_science.py`
- `backend/app/repositories/lab_science.py`
- `backend/app/services/lab_science.py`
- `backend/alembic/versions/20260730_0002_a2_science_authority.py`
- `backend/tests/unit/test_a2_science_schema.py`
- `backend/tests/unit/test_a2_science_service.py`
- `backend/tests/integration/test_a2_science_migration.py`
- `backend/tests/integration/test_a2_science_transactions.py`
- `backend/tests/integration/test_a2_science_export.py`
- `docs/verification/a2_slice2/README.md`

### Modify

- `backend/app/models/lab.py`
- `backend/app/repositories/lab.py`
- `backend/app/services/lab_service.py`
- `backend/app/services/lab_export.py`
- `backend/tests/unit/test_lab_schema.py`
- `backend/tests/integration/test_backup_restore.py`

### Protected from this slice

- `backend/app/api/v1/endpoints/lab.py`
- `backend/app/schemas/lab.py`
- `backend/tests/integration/test_lab_api.py`
- all `engine/analytical/*` files
- `engine/safety/regulatory.py`
- both legacy `AuthorityVector` definitions
- `perfume_chem.db`
- `data/perfumery_kb.db`, except restoration of a verified test side effect
- every historical migration file

## Canonical schema contract

The module declares:

```python
SCIENCE_AUTHORITY_TABLE_NAMES = {
    "lab_analytical_method_versions",
    "lab_analytical_runs",
    "lab_analytical_peaks",
    "lab_analytical_qc_records",
    "lab_analytical_attachments",
    "lab_gco_events",
    "lab_regulatory_assessment_versions",
    "lab_regulatory_findings",
    "lab_claim_assessment_versions",
    "lab_claim_assessment_evidence_links",
}
```

Every table is append-only, inherits immutable `id` and `created_at` behavior
from `LabRecord`, omits `updated_at`, uses named constraints, and has matching
SQLite update/delete denial triggers in the migration.

### `LabAnalyticalMethodVersion`

Purpose: immutable definition of an analytical method.

Required fields:

```text
id
method_id
version_number
schema_version
technique
intended_use
status
method_json
evidence_record_id
content_sha256
parent_version_id
parent_sha256
created_at
```

Required database contracts:

- unique `(method_id, version_number)`;
- unique `content_sha256`;
- `version_number >= 1`;
- `parent_version_id` self-FK with `RESTRICT`;
- evidence FK to `lab_evidence_records`;
- technique is one of `GCMS`, `HS_SPME_GCMS`, `GC_O`, `OTHER`;
- status is one of `DRAFT`, `VALIDATED`, `RETIRED`;
- version 1 has no parent; later versions require a parent and matching
  service-validated hash continuity.

### `LabAnalyticalRun`

Purpose: one immutable acquisition/processing record bound to a method
version.

Required fields:

```text
id
run_id
method_version_id
run_kind
status
instrument_identifier
acquired_at
parameters_json
deviations_json
processing_version
experiment_id
sample_id
bottle_id
formula_version_id
build_plan_version_id
content_sha256
created_at
```

Required contracts:

- unique `run_id`;
- unique `content_sha256`;
- method-version FK;
- optional FKs to existing experiment, sample, bottle, formula version, and
  A2 build-plan version tables;
- run kind is one of `GCMS`, `HS_SPME_GCMS`, `GC_O`, `OTHER`;
- status is one of `ACQUIRED`, `PROCESSED`, `QC_ACCEPTED`, `QC_REJECTED`;
- at least one subject reference among sample, bottle, formula version,
  build-plan version, or experiment is required;
- timestamps must be timezone-aware at the service boundary.

### `LabAnalyticalPeak`

Purpose: immutable detected feature or peak.

Required fields:

```text
id
analytical_run_id
peak_key
retention_time_minutes
retention_index
area
response_factor
qualifier_ions_json
tentative_identity
material_id
identity_state
match_score
quantitation_basis
quantity
quantity_unit
standard_uncertainty
notes
content_sha256
created_at
```

Required contracts:

- unique `(analytical_run_id, peak_key)`;
- unique `content_sha256`;
- run FK and optional material FK;
- retention time, retention index, area, response factor, quantity, and
  uncertainty are nonnegative when supplied;
- match score is within `[0, 1]` when supplied;
- identity state is one of `UNASSIGNED`, `TENTATIVE`, `CONFIRMED`;
- a confirmed identity requires `material_id`;
- quantity requires both an explicit unit and quantitation basis.

### `LabAnalyticalQCRecord`

Purpose: immutable QC criterion and observed outcome for a run.

Required fields:

```text
id
analytical_run_id
qc_key
qc_type
status
criteria_json
observed_json
evidence_record_id
content_sha256
created_at
```

Required contracts:

- unique `(analytical_run_id, qc_key)`;
- unique `content_sha256`;
- run FK and optional evidence FK;
- status is one of `PASS`, `FAIL`, `UNKNOWN`, `NOT_APPLICABLE`;
- `UNKNOWN` remains fail-closed for downstream exact claims.

### `LabAnalyticalAttachment`

Purpose: immutable external-file binding without file contents.

Required fields:

```text
id
analytical_run_id
attachment_kind
media_type
byte_length
content_sha256
storage_locator
evidence_record_id
created_at
```

Required contracts:

- unique `(analytical_run_id, attachment_kind, content_sha256)`;
- run FK and optional evidence FK;
- `byte_length >= 0`;
- SHA-256 is exactly 64 lowercase hexadecimal characters at the service
  boundary;
- raw bytes are not accepted by the command DTO.

### `LabGCOEvent`

Purpose: immutable GC-olfactometry observation linked to a run and optionally
to a peak.

Required fields:

```text
id
analytical_run_id
analytical_peak_id
event_key
retention_time_minutes
retention_index
descriptor
intensity
assessor_pseudonym
repeatability_json
evidence_record_id
content_sha256
created_at
```

Required contracts:

- unique `(analytical_run_id, event_key)`;
- unique `content_sha256`;
- run FK, optional peak FK, optional evidence FK;
- a linked peak must belong to the same run, enforced by a composite FK;
- position fields are nonnegative when supplied;
- intensity is within `[0, 1]` when supplied;
- assessor identity is pseudonymous and nonblank.

### `LabRegulatoryAssessmentVersion`

Purpose: immutable dated evaluation of a subject against an identified
regulatory source state.

Required fields:

```text
id
assessment_id
version_number
schema_version
subject_type
subject_id
parent_version_id
standard_identifier
standard_amendment
standard_state
source_evidence_record_id
jurisdiction
product_category
concentration_basis
finished_product_concentration
effective_date
evaluated_at
result_state
assumptions_json
unresolved_json
permitted_wording
content_sha256
parent_sha256
created_at
```

Required contracts:

- unique `(assessment_id, version_number)`;
- unique `content_sha256`;
- `version_number >= 1`;
- parent self-FK and source-evidence FK;
- subject type is one of `FORMULA_VERSION`, `BUILD_PLAN_VERSION`, `BOTTLE`;
- service validates that `subject_id` exists in the named subject table;
- standard state is one of `CURRENT`, `SUPERSEDED`, `UNKNOWN`;
- result state is one of `PASS`, `FAIL`, `UNKNOWN`, `CONFLICT`;
- finished concentration is nonnegative when supplied;
- `PASS` requires current standard state, evidence, and no unresolved items;
- `UNKNOWN` and `CONFLICT` never permit exact compliance wording.

### `LabRegulatoryFinding`

Purpose: immutable per-substance or per-rule result belonging to one
assessment version.

Required fields:

```text
id
regulatory_assessment_version_id
finding_key
restriction_id
material_id
substance_identity
observed_fraction
maximum_fraction
concentration_basis
result_state
detail
evidence_record_id
content_sha256
created_at
```

Required contracts:

- unique `(regulatory_assessment_version_id, finding_key)`;
- unique `content_sha256`;
- assessment FK and optional restriction/material/evidence FKs;
- observed and maximum fractions are nonnegative when supplied;
- result state is one of `PASS`, `FAIL`, `UNKNOWN`, `CONFLICT`;
- a `PASS` finding requires both observed and maximum fractions with the same
  explicit basis.

### `LabClaimAssessmentVersion`

Purpose: immutable claim-specific authority decision.

Required fields:

```text
id
claim_id
version_number
schema_version
claim_type
subject_type
subject_id
parent_version_id
policy_version
decision
authority_json
missing_evidence_json
conflicts_json
permitted_wording
forbidden_wording
human_review_state
reviewer_pseudonym
reviewed_at
content_sha256
parent_sha256
created_at
```

Required contracts:

- unique `(claim_id, version_number)`;
- unique `content_sha256`;
- `version_number >= 1`;
- parent self-FK;
- subject type is one of `ANALYTICAL_RUN`, `REGULATORY_ASSESSMENT`,
  `FORMULA_VERSION`, `BUILD_PLAN_VERSION`, `BOTTLE`, `EXPERIMENT`;
- service validates subject existence;
- decision is one of `ALLOW_EXACT`, `ALLOW_SCOPED`, `ADVISORY_ONLY`,
  `WITHHOLD_UNKNOWN`, `BLOCK`;
- human review state is one of `NOT_REQUIRED`, `PENDING`, `APPROVED`,
  `REJECTED`;
- `ALLOW_EXACT` requires nonempty direct evidence links, no missing evidence,
  no conflicts, nonblank permitted wording, and any policy-required human
  review;
- this record is not a release decision.

### `LabClaimAssessmentEvidenceLink`

Purpose: typed evidence membership for one claim-assessment version.

Required fields:

```text
id
claim_assessment_version_id
evidence_record_id
role
created_at
```

Required contracts:

- unique `(claim_assessment_version_id, evidence_record_id, role)`;
- assessment and evidence FKs;
- role is one of `DIRECT`, `SUPPORTING`, `CONTRADICTING`,
  `LIMITATION`;
- no authority is inferred merely from link existence.

## Service contract

`backend/app/services/lab_science.py` supplies frozen, slotted command DTOs,
domain errors with stable `code` values, and `LabScienceServiceMixin`.

The service methods are:

```text
create_analytical_method_version
record_analytical_run
record_analytical_peak
record_analytical_qc
bind_analytical_attachment
record_gco_event
create_regulatory_assessment_version
record_regulatory_finding
create_claim_assessment_version
```

Every method:

1. normalizes and validates caller input;
2. resolves all referenced canonical rows;
3. builds a deterministic normalized payload;
4. hashes it with `engine.calibration.hashing.stable_json_hash`;
5. enters `LabService._transaction()`;
6. inserts only immutable rows through `LabRepository`;
7. returns the canonical record;
8. never calls `commit` or `rollback` in a repository.

Parent versions must match the same stable identity and immediately preceding
version number. Parent hashes must match persisted content hashes.

Claim and regulatory services fail closed. Missing rows, unknown standard
state, absent direct evidence, unresolved conflicts, and pending required
review cannot yield exact authority.

## Export contract

Add:

```python
_FORMAT_REVISION_V3 = "lab-export-v3"
_SCIENCE_AUTHORITY_TABLE_ORDER = (...)
```

Required behavior:

- `export_workspace()` keeps its default `lab-export-v1`;
- `export_planning_workspace()` continues writing v2 only;
- add `export_science_workspace()` to write the complete v3 graph;
- `canonical_bytes()` writes v3 because v3 is the newest complete authority
  graph;
- imports accept v1, v2, and v3;
- importing v1 or v2 creates no science-authority rows;
- v3 table order follows all foreign-key dependencies;
- round-trip bytes are deterministic;
- UUID conflicts with different content remain errors;
- ordering contracts explicitly cover method versions, runs, peaks, QC,
  GC-O events, regulatory versions/findings, claim versions, and evidence
  links;
- no attachment bytes are present in the packet.

## Task 1: Freeze entry state

- [ ] Reconfirm HEAD, branch, dirty-entry count, canonical database hash,
  knowledge database hash, protected file hashes, and recovery verification.
- [ ] Reconfirm one Alembic head: `20260730_0001`.
- [ ] Record the DeepLuna job ID and locally verify its cited conventions.
- [ ] Stage and commit only this plan as
  `docs: plan A2 science authority persistence`.

## Task 2: Write RED schema and migration tests

### Files

- Create `backend/tests/unit/test_a2_science_schema.py`.
- Create `backend/tests/integration/test_a2_science_migration.py`.
- Modify `backend/tests/unit/test_lab_schema.py`.

### RED contracts

- [ ] Assert all ten tables exist in `Base.metadata`.
- [ ] Assert all ten are in `APPEND_ONLY_TABLES`.
- [ ] Assert no table has `updated_at`.
- [ ] Assert required named unique and check constraints.
- [ ] Assert every expected foreign key and composite ownership key.
- [ ] Assert empty database upgrade reaches `20260730_0002`.
- [ ] Assert upgrade from `20260730_0001` preserves representative legacy and
  Slice 1 rows byte-for-byte at the row level.
- [ ] Assert downgrade returns to `20260730_0001` and removes only Slice 2
  tables/triggers.
- [ ] Assert SQLite integrity is `ok`.
- [ ] Assert one Alembic head.
- [ ] Assert update/delete denial triggers on all ten tables.
- [ ] Assert database checks reject invalid versions, states, negative
  quantities, scores outside `[0, 1]`, missing required subject references,
  inconsistent confirmed identities, and broken foreign keys.
- [ ] Run focused schema/migration tests and capture the expected RED failures
  before production files exist.

## Task 3: Implement ORM models and explicit migration

### Files

- Create `backend/app/models/lab_science.py`.
- Modify `backend/app/models/lab.py`.
- Create
  `backend/alembic/versions/20260730_0002_a2_science_authority.py`.

### Implementation

- [ ] Add the ten ORM records and exported table-name set.
- [ ] Import the records in `app.models.lab` before `LAB_TABLE_NAMES` is
  computed.
- [ ] Include all ten names in `APPEND_ONLY_TABLES`.
- [ ] Implement an explicit Alembic migration with no metadata reflection,
  autogenerate dependency, or production-data mutation.
- [ ] Create tables in dependency order.
- [ ] Create update/delete denial triggers for every new table.
- [ ] Downgrade drops triggers and tables in reverse dependency order.
- [ ] Run schema and migration tests to GREEN.

## Task 4: Write RED service contracts

### Files

- Create `backend/tests/unit/test_a2_science_service.py`.
- Create `backend/tests/integration/test_a2_science_transactions.py`.

### Required RED cases

- [ ] Method version one succeeds with evidence and deterministic hash.
- [ ] Method version two requires the same stable method ID, immediate parent,
  and parent hash continuity.
- [ ] A run requires a method and at least one canonical subject.
- [ ] Peak identity, quantity, and score rules fail closed.
- [ ] QC `UNKNOWN` cannot support exact authority.
- [ ] Attachment binding accepts only digest metadata and rejects malformed
  SHA-256 values.
- [ ] GC-O peak ownership is validated.
- [ ] Regulatory subjects must exist.
- [ ] Regulatory `PASS` requires current authority, source evidence, and no
  unresolved items.
- [ ] A finding cannot claim `PASS` without comparable explicit fractions.
- [ ] Claim subjects must exist.
- [ ] `ALLOW_EXACT` fails without direct evidence, with missing evidence, with
  conflicts, or with unsatisfied human review.
- [ ] Reusing the same stable identity/version with the same normalized
  payload is deterministic; conflicting payloads are rejected.
- [ ] A failed multi-row command leaves no partial record.
- [ ] Concurrent creation of the same next version yields one accepted row and
  one stable conflict.
- [ ] Run focused service/transaction tests and capture RED.

## Task 5: Implement repository and service composition

### Files

- Create `backend/app/repositories/lab_science.py`.
- Modify `backend/app/repositories/lab.py`.
- Create `backend/app/services/lab_science.py`.
- Modify `backend/app/services/lab_service.py`.

### Implementation

- [ ] Add science-authority query helpers without transaction ownership.
- [ ] Compose `LabScienceRepositoryMixin` into `LabRepository`.
- [ ] Add frozen command DTOs and stable domain errors.
- [ ] Use `stable_json_hash`; do not introduce a second hashing algorithm.
- [ ] Compose `LabScienceServiceMixin` into `LabService`.
- [ ] Reuse `LabService._transaction()` for every write.
- [ ] Validate parent chains and polymorphic subject existence.
- [ ] Validate evidence-link roles and direct-evidence requirements.
- [ ] Never calculate or persist a legacy `AuthorityVector`.
- [ ] Run unit and transaction tests to GREEN.

## Task 6: Write RED export/import and backup contracts

### Files

- Create `backend/tests/integration/test_a2_science_export.py`.
- Modify `backend/tests/integration/test_backup_restore.py`.

### Required RED cases

- [ ] v3 exports a complete representative science-authority graph.
- [ ] ordering follows FK dependencies and stable identity/version keys.
- [ ] v3 round-trip is byte-deterministic and idempotent.
- [ ] v1 import creates no planning or science-authority rows.
- [ ] v2 import creates no science-authority rows.
- [ ] v1 endpoint default remains v1.
- [ ] planning export remains v2.
- [ ] canonical bytes use v3.
- [ ] attachment exports contain digest metadata and no raw bytes.
- [ ] UUID conflict with different content fails atomically.
- [ ] backup/restore expectations bind to Alembic head `20260730_0002`.
- [ ] Run export and backup tests and capture RED.

## Task 7: Implement v3 export/import

### Files

- Modify `backend/app/services/lab_export.py`.

### Implementation

- [ ] Add explicit v3 constants and table order.
- [ ] Keep the v1 default and v2 planning writer unchanged.
- [ ] Add `export_science_workspace()`.
- [ ] Make `canonical_bytes()` use v3.
- [ ] Accept v1/v2/v3 import packets without inventing missing authority.
- [ ] Add deterministic ordering, unit, provenance, and attachment contracts.
- [ ] Run export, backup, v1 compatibility, and Slice 1 export tests to GREEN.

## Task 8: Focused and broad verification

### Focused gate

Run from `backend` with ANSI disabled:

```powershell
poetry run pytest `
  tests/unit/test_a2_science_schema.py `
  tests/unit/test_a2_science_service.py `
  tests/integration/test_a2_science_migration.py `
  tests/integration/test_a2_science_transactions.py `
  tests/integration/test_a2_science_export.py `
  -q --color=no
```

Expected: all pass, zero skips.

### Compatibility gate

```powershell
poetry run pytest `
  tests/unit/test_a2_planning_schema.py `
  tests/unit/test_a2_planning_service.py `
  tests/integration/test_a2_planning_migration.py `
  tests/integration/test_a2_planning_transactions.py `
  tests/integration/test_a2_planning_export.py `
  tests/integration/test_a2_planning_api.py `
  tests/integration/test_lab_api.py `
  tests/integration/test_backup_restore.py `
  -q --color=no
```

Expected: all pass.

### Static and complete backend gates

```powershell
poetry run ruff check app alembic tests
poetry run mypy app --ignore-missing-imports
poetry run pytest -q --color=no `
  --basetemp=../output/verification-temp/a2-slice2-backend `
  --junitxml=../verification_runs/a2-slice2-backend.xml
```

Expected: all commands exit zero.

### Root and canonical verifier gates

Using the supported root Python 3.11 environment:

```powershell
python -m pytest -q --color=no `
  --basetemp=output/verification-temp/a2-slice2-root `
  --junitxml=verification_runs/a2-slice2-root.xml
python scripts/pipeline_audit.py project-verify --json
```

Expected:

- root suite passes;
- package and wheel smoke pass;
- migration, backup/restore, and golden locks pass;
- only declared optional Docker checks may skip;
- no scientific release is inferred.

All commands use explicit process timeouts in the executor and preserve
stdout/stderr. No PTY is used.

## Task 9: Restore verifier side effects and record evidence

- [ ] If the canonical verifier mutates `data/perfumery_kb.db`, restore it from
  the verified recovery bytes and prove SHA-256 and SQLite integrity.
- [ ] Prove `perfume_chem.db` remains zero bytes with its protected SHA-256.
- [ ] Prove the three protected legacy endpoint/schema/test hashes remain
  unchanged.
- [ ] Create `docs/verification/a2_slice2/README.md`.
- [ ] Record starting/ending commit, changed paths, RED/GREEN commands and
  counts, migration-copy results, rollback result, export revisions, database
  hashes, verifier result, optional skips, DeepLuna job IDs, rejected worker
  interpretations, and limitations.
- [ ] State:
  `A2_SLICE2_PASS=true`, `A2_COMPLETE=false`, `A3_STARTED=false`, and
  `SCIENTIFIC_RELEASE_BLOCKED=true` only if the executable evidence supports
  those values.

## Task 10: Bounded checkpoint

- [ ] Stage only paths locked by this plan.
- [ ] Verify the staged set contains no environment file, secret, database,
  archive, generated wheel, unrelated dirty path, legacy engine modification,
  Slice 3 work, or A3 work.
- [ ] Commit:

```powershell
git commit -m "build(a2): add science authority persistence"
```

- [ ] Record the checkpoint and continue automatically to A2 Slice 3 because
  the user has already authorized A through D execution.
- [ ] If any A2.2 exit criterion is RED, do not commit and do not begin Slice
  3; diagnose and repair within this scope.

## A2.2 exit gate

The slice passes only when:

- all ten canonical tables exist in ORM metadata and explicit migration;
- all ten tables are database-enforced append-only;
- empty and `20260730_0001` upgrade paths pass;
- downgrade returns cleanly to `20260730_0001`;
- one Alembic head exists;
- analytical methods are versioned and evidence-linked;
- runs bind method, acquisition, processing, and at least one subject;
- peaks preserve identity state, quantitation basis, units, and uncertainty;
- QC unknown/fail states remain explicit;
- attachments store digest metadata only;
- GC-O events are run/peak-consistent and pseudonymous;
- regulatory assessments are dated, source-linked, versioned, and fail closed;
- findings preserve explicit fractions and bases;
- claim authority is claim-specific and evidence-linked;
- no legacy `AuthorityVector` is persisted;
- exact authority cannot be created with missing/conflicting evidence;
- repositories do not own transactions;
- v1 and v2 imports invent no science authority;
- v3 export/import is deterministic and idempotent;
- old API and Slice 1 compatibility tests remain green;
- full backend, root, artifact, package, wheel, migration, backup, and verifier
  gates pass;
- existing dirty work and protected database bytes remain preserved;
- a bounded checkpoint SHA exists.

Passing this gate does not complete A2, Build A, or scientific release.
