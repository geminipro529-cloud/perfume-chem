# Build B1 Source Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` task-by-task. Codex subagents are prohibited by
> project policy; an eligible DeepLuna Fast read may assist only after a fresh
> exact-project `deepseek_check` returns `READY`.

**Goal:** Add an append-only canonical source-document, extraction, workflow,
and derivation registry that reconstructs every accepted source-to-observation
path without promoting legacy or machine-extracted values.

**Architecture:** Four new canonical SQLAlchemy tables live in a focused
`lab_sources` module and join the existing `LabService`/`LabRepository`
composition. Writes are immutable, hash-addressed service commands; workflow
changes are append-only events. Alembic revision `20260730_0005` creates only
the B1 schema and performs no backfill.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x async ORM, Alembic, SQLite,
pytest/pytest-asyncio, Ruff, mypy, existing `stable_json_hash`.

---

## File Map

- Create `backend/app/models/lab_sources.py`: B1 constants and four canonical
  ORM models.
- Modify `backend/app/models/lab.py`: import B1 models and register their tables
  as append-only.
- Create `backend/app/repositories/lab_sources.py`: deterministic source,
  extraction, workflow, and derivation reads.
- Modify `backend/app/repositories/lab.py`: compose the B1 repository mixin.
- Create `backend/app/services/lab_sources.py`: validated inputs, state machine,
  immutable writes, cycle detection, and derivation reconstruction.
- Modify `backend/app/services/lab_service.py`: compose the B1 service mixin.
- Create `backend/alembic/versions/20260730_0005_b1_source_provenance.py`:
  linear schema migration and SQLite append-only triggers.
- Create `backend/tests/unit/test_b1_source_schema.py`: metadata and database
  constraint contract.
- Create `backend/tests/unit/test_b1_source_service.py`: source, extraction,
  workflow, independence, and reconstruction behavior.
- Create `backend/tests/integration/test_b1_source_migration.py`: empty,
  representative, downgrade/re-upgrade, and append-only migration behavior.
- Create `docs/verification/b1/source_provenance_gate.md` and
  `docs/verification/b1/source_provenance_gate.json`: reproducible B1 evidence.

### Task 1: Freeze the B1 schema contract

**Files:**

- Create: `backend/tests/unit/test_b1_source_schema.py`
- Create: `backend/app/models/lab_sources.py`
- Modify: `backend/app/models/lab.py`

- [ ] **Step 1: Write the failing schema test**

The test must import the B1 constants/models and assert the exact contract:

```python
REQUIRED_SOURCE_TYPES = {
    "AUTHENTICATED_FORMULA_OR_DOSSIER",
    "PRIMARY_PEER_REVIEWED_PAPER",
    "REVIEW_PAPER",
    "STANDARD",
    "REGULATION_OR_OFFICIAL_GUIDANCE",
    "AUTHORITATIVE_DATABASE_RECORD",
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
    "PATENT",
    "LOCAL_ANALYTICAL_EXPERIMENT",
    "LOCAL_SENSORY_EXPERIMENT",
    "EXPERT_NOTE",
    "SECONDARY_RECONSTRUCTION",
    "COMMUNITY_OBSERVATION",
    "AI_GENERATED_HYPOTHESIS",
}

REQUIRED_WORKFLOW_STATES = {
    "STAGED", "PARSED", "IDENTITY_RESOLVED", "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED", "CONFLICT_CHECKED", "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE", "REJECTED", "SUPERSEDED",
}

def test_b1_tables_are_canonical_append_only_and_complete():
    assert set(SOURCE_TYPES) == REQUIRED_SOURCE_TYPES
    assert set(EVIDENCE_WORKFLOW_STATES) == REQUIRED_WORKFLOW_STATES
    assert SOURCE_AUTHORITY_TABLE_NAMES <= LAB_TABLE_NAMES
    assert SOURCE_AUTHORITY_TABLE_NAMES <= APPEND_ONLY_TABLES
    assert SOURCE_AUTHORITY_TABLE_NAMES == {
        "lab_source_document_versions",
        "lab_source_derivation_links",
        "lab_source_extraction_records",
        "lab_evidence_workflow_events",
    }
```

Also inspect table constraints for positive versions/sequences, valid choices,
unique source versions, unique record digests, no self-derivation, and required
foreign keys.

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/unit/test_b1_source_schema.py -q
```

Expected: collection failure because `app.models.lab_sources` does not exist.

- [ ] **Step 3: Implement the minimal ORM schema**

Define exact constants:

```python
SOURCE_TYPES = (
    "AUTHENTICATED_FORMULA_OR_DOSSIER",
    "PRIMARY_PEER_REVIEWED_PAPER",
    "REVIEW_PAPER",
    "STANDARD",
    "REGULATION_OR_OFFICIAL_GUIDANCE",
    "AUTHORITATIVE_DATABASE_RECORD",
    "SUPPLIER_COA",
    "SUPPLIER_SPECIFICATION",
    "SUPPLIER_SDS",
    "SUPPLIER_IFRA_CERTIFICATE",
    "SUPPLIER_ALLERGEN_DECLARATION",
    "PATENT",
    "LOCAL_ANALYTICAL_EXPERIMENT",
    "LOCAL_SENSORY_EXPERIMENT",
    "EXPERT_NOTE",
    "SECONDARY_RECONSTRUCTION",
    "COMMUNITY_OBSERVATION",
    "AI_GENERATED_HYPOTHESIS",
)
EVIDENCE_WORKFLOW_STATES = (
    "STAGED", "PARSED", "IDENTITY_RESOLVED", "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED", "CONFLICT_CHECKED", "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE", "REJECTED", "SUPERSEDED",
)
SOURCE_REVIEW_STATES = ("UNREVIEWED", "REVIEWED", "REJECTED", "SUPERSEDED")
SOURCE_DERIVATION_RELATIONS = (
    "DERIVED_FROM", "REPRODUCES", "CITES", "INCORPORATES",
)
WORKFLOW_SUBJECT_TYPES = ("SOURCE_VERSION", "EXTRACTION_RECORD")
```

Implement the four classes from the design with `LabRecord`, JSON defaults
using `server_default`, explicit checks, unique constraints, `RESTRICT`
foreign keys, and no ORM cascade deletion. Export
`SOURCE_AUTHORITY_TABLE_NAMES`. Import the models at the bottom of
`app/models/lab.py` before `LAB_TABLE_NAMES` is computed and union the table
set into `APPEND_ONLY_TABLES`.

- [ ] **Step 4: Run schema test and Ruff**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/unit/test_b1_source_schema.py -q
& .\.venv\Scripts\poetry.exe run ruff check `
  backend/app/models/lab_sources.py backend/app/models/lab.py `
  backend/tests/unit/test_b1_source_schema.py
```

Expected: all schema tests pass; Ruff reports no errors.

- [ ] **Step 5: Commit the bounded schema slice**

```powershell
git add -- backend/app/models/lab_sources.py backend/app/models/lab.py `
  backend/tests/unit/test_b1_source_schema.py
git commit -m "feat: add B1 canonical source schema"
```

### Task 2: Add the linear, no-backfill migration

**Files:**

- Create: `backend/tests/integration/test_b1_source_migration.py`
- Create: `backend/alembic/versions/20260730_0005_b1_source_provenance.py`

- [ ] **Step 1: Write migration tests first**

Reuse `_alembic_config`, `_version`, and representative A5 setup patterns from
`backend/tests/integration/test_a5_operations_migration.py`. Tests must assert:

```python
B1_HEAD = "20260730_0005"
B1_TABLES = {
    "lab_source_document_versions",
    "lab_source_derivation_links",
    "lab_source_extraction_records",
    "lab_evidence_workflow_events",
}
```

- empty database upgrades to B1 head;
- a representative A5 database upgrades while legacy table names, row counts,
  and selected row hashes remain unchanged;
- all B1 tables start empty, proving no backfill;
- update/delete against every B1 table raises SQLite `IntegrityError` with
  `append-only`;
- downgrade reaches `20260730_0004`, removes only B1 tables, and re-upgrade
  returns to B1;
- migration text contains no introspective `has_table`, silent skip, or data
  insertion.

- [ ] **Step 2: Run migration tests and verify RED**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/integration/test_b1_source_migration.py -q
```

Expected: failure because revision `20260730_0005` is absent.

- [ ] **Step 3: Implement the migration**

Create an explicit migration with:

```python
revision = "20260730_0005"
down_revision = "20260730_0004"
```

Create tables in dependency order: source versions, derivation links,
extractions, workflow events. Create indexes for stable source ID,
independence group, source-version extraction lookup, output observation ID,
workflow subject, and parent/child derivation traversal. Install the same
SQLite append-only trigger pattern used by revision `20260730_0002`. Downgrade
drops triggers, indexes, and tables in reverse order. Do not execute `INSERT`,
`UPDATE`, or legacy-table DDL.

- [ ] **Step 4: Verify migration and schema together**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/integration/test_b1_source_migration.py `
  backend/tests/unit/test_b1_source_schema.py -q
& .\.venv\Scripts\poetry.exe run ruff check `
  backend/alembic/versions/20260730_0005_b1_source_provenance.py `
  backend/tests/integration/test_b1_source_migration.py
```

Expected: both files pass; Ruff clean.

- [ ] **Step 5: Commit the migration slice**

```powershell
git add -- backend/alembic/versions/20260730_0005_b1_source_provenance.py `
  backend/tests/integration/test_b1_source_migration.py
git commit -m "feat: migrate B1 source provenance schema"
```

### Task 3: Register immutable source versions

**Files:**

- Create: `backend/tests/unit/test_b1_source_service.py`
- Create: `backend/app/repositories/lab_sources.py`
- Modify: `backend/app/repositories/lab.py`
- Create: `backend/app/services/lab_sources.py`
- Modify: `backend/app/services/lab_service.py`

- [ ] **Step 1: Write source-registration tests**

Construct `SourceDocumentInput` with a real 64-character fixture digest and
assert:

```python
first = await service.register_source_document(command)
second = await service.register_source_document(replace(command, title="v2"), parent_version_id=first.id)
assert first.source_id == second.source_id
assert (first.version_number, second.version_number) == (1, 2)
assert second.supersedes_version_id == first.id
assert second.parent_record_sha256 == first.record_sha256
assert second.record_sha256 != first.record_sha256
assert (await service.effective_workflow_state("SOURCE_VERSION", first.id)) == "STAGED"
```

Reject blank titles/groups, unsupported types, malformed digests,
absolute/traversing preserved paths, missing/nonlatest parents, and duplicate
record payloads. Confirm no legacy evidence row is created.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/unit/test_b1_source_service.py -k "source_document" -q
```

Expected: collection failure because B1 service types are absent.

- [ ] **Step 3: Implement repository reads and source registration**

`LabSourceRepositoryMixin` must provide:

```python
async def get_source_document_version(self, version_id: str) -> LabSourceDocumentVersion | None
async def latest_source_document_version(self, source_id: str) -> LabSourceDocumentVersion | None
async def source_record_by_hash(self, record_sha256: str) -> LabSourceDocumentVersion | None
async def workflow_events(self, subject_type: str, subject_id: str) -> list[LabEvidenceWorkflowEvent]
```

`SourceDocumentInput.__post_init__` validates/copies every field. The service
builds a canonical payload under schema `lab-source-document-v1`, hashes it
with `stable_json_hash`, writes the source row and an initial sequence-1
`STAGED` workflow event in one existing `_transaction()` context, and never
writes `LabEvidenceRecord`.

- [ ] **Step 4: Verify source behavior**

Run the focused service test, schema test, and Ruff on all five changed files.
Expected: pass and no lint errors.

- [ ] **Step 5: Commit the source service slice**

```powershell
git add -- backend/app/repositories/lab_sources.py `
  backend/app/repositories/lab.py backend/app/services/lab_sources.py `
  backend/app/services/lab_service.py `
  backend/tests/unit/test_b1_source_service.py
git commit -m "feat: register immutable B1 source versions"
```

### Task 4: Preserve extraction context and enforce workflow

**Files:**

- Modify: `backend/tests/unit/test_b1_source_service.py`
- Modify: `backend/app/repositories/lab_sources.py`
- Modify: `backend/app/services/lab_sources.py`

- [ ] **Step 1: Write failing extraction/workflow tests**

Create an extraction with table context:

```python
ExtractionRecordInput(
    source_version_id=source.id,
    locator={"page": 12, "table": "2", "row": "Linalool"},
    structure_context={
        "column_heading": "Odor threshold",
        "unit_heading": "microgram/m3",
        "footnotes": ["measured at 25 C in air"],
    },
    original_wording="Linalool 7.0 microgram/m3",
    original_value={"value": "7.0", "unit": "microgram/m3"},
    parsed_value={"value": 7.0},
    normalization={"target_unit": "microgram/m3", "factor": 1.0},
    parser_or_model_version="manual-parser/1",
    reviewer_pseudonym=None,
    uncertainty={"kind": "not_reported"},
    ambiguity=[],
    output_observation_id=observation_id,
    input_sha256="b" * 64,
    output_sha256="c" * 64,
)
```

Assert all structure survives round-trip and starts `STAGED`. Append every
ordered event through `ACCEPTED_FOR_SCOPED_USE`; acceptance must require the
prior `HUMAN_REVIEWED` event, reviewer, nonempty scope, locator, output
observation, and digests. Assert skipped transitions, terminal transitions,
blank reviewers, and AI-generated staged records fail closed. Assert no state
before acceptance is authoritative.

- [ ] **Step 2: Run and verify RED**

Run the new tests with `-k "extraction or workflow"`. Expected: missing methods
or assertions fail.

- [ ] **Step 3: Implement minimal extraction and state machine**

Use this ordered normal path:

```python
NORMAL_WORKFLOW = (
    "STAGED", "PARSED", "IDENTITY_RESOLVED", "UNIT_NORMALIZED",
    "CONDITION_NORMALIZED", "CONFLICT_CHECKED", "HUMAN_REVIEWED",
    "ACCEPTED_FOR_SCOPED_USE",
)
```

Allow any nonterminal state to `REJECTED`; allow only
`ACCEPTED_FOR_SCOPED_USE -> SUPERSEDED`. Each event sequence is previous
sequence plus one and each event has a stable hash. Add repository reads by
source version, output observation ID, and effective state. Expose
`is_accepted_for_scoped_use()` only as an exact state-and-scope predicate; do
not connect it to production scientific consumers.

- [ ] **Step 4: Verify focused and combined B1 tests**

Run service and schema tests plus Ruff. Expected: pass, no warnings or errors.

- [ ] **Step 5: Commit the workflow slice**

```powershell
git add -- backend/app/repositories/lab_sources.py `
  backend/app/services/lab_sources.py `
  backend/tests/unit/test_b1_source_service.py
git commit -m "feat: enforce B1 extraction workflow"
```

### Task 5: Model independence and reconstruct derivations

**Files:**

- Modify: `backend/tests/unit/test_b1_source_service.py`
- Modify: `backend/app/repositories/lab_sources.py`
- Modify: `backend/app/services/lab_sources.py`

- [ ] **Step 1: Write failing derivation tests**

Create primary, review, and website source versions where the review and
website derive from the same primary source. Assert:

```python
graph = await service.reconstruct_observation_derivation(
    observation_id,
    required_scope="threshold_screening",
)
assert graph["observation_id"] == observation_id
assert graph["complete"] is True
assert graph["independence_groups"] == ["primary-lineage"]
assert {edge["relation"] for edge in graph["derivation_links"]} == {
    "DERIVED_FROM"
}
assert graph["extractions"][0]["effective_state"] == "ACCEPTED_FOR_SCOPED_USE"
```

Reject self-links, duplicate links, and cycles. A missing source, extraction,
state path, locator, or output observation returns a stable incomplete result
and cannot be accepted as complete.

- [ ] **Step 2: Run and verify RED**

Run with `-k "derivation or independence or reconstruct"`. Expected: missing
link/reconstruction methods fail.

- [ ] **Step 3: Implement links, cycle detection, and reconstruction**

Traverse parent links deterministically by `(relation, parent id, child id)`.
Before insertion, depth-first search from the proposed parent must not reach
the child. Reconstruction must return sorted JSON-safe records containing
source IDs/versions/types/digests, derivation edges, extraction context,
workflow events, effective state, uncertainty, and unique independence groups.
`reconstruct_observation_derivation(observation_id, *, required_scope)` requires
a nonblank scope. `complete` is true only when at least one matching extraction
is accepted for that exact scope and every referenced record exists.

- [ ] **Step 4: Verify all B1 unit tests and type/lint checks**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/unit/test_b1_source_schema.py `
  backend/tests/unit/test_b1_source_service.py -q
& .\.venv\Scripts\poetry.exe run ruff check `
  backend/app/models/lab_sources.py backend/app/repositories/lab_sources.py `
  backend/app/services/lab_sources.py backend/tests/unit/test_b1_source_schema.py `
  backend/tests/unit/test_b1_source_service.py
& .\.venv\Scripts\poetry.exe run mypy backend/app/models/lab_sources.py `
  backend/app/repositories/lab_sources.py backend/app/services/lab_sources.py
```

Expected: all commands exit zero.

- [ ] **Step 5: Commit the derivation slice**

```powershell
git add -- backend/app/repositories/lab_sources.py `
  backend/app/services/lab_sources.py `
  backend/tests/unit/test_b1_source_service.py
git commit -m "feat: reconstruct B1 source derivations"
```

### Task 6: Run the B1 exit gate and record evidence

**Files:**

- Create: `docs/verification/b1/source_provenance_gate.md`
- Create: `docs/verification/b1/source_provenance_gate.json`

- [ ] **Step 1: Run focused B1 verification**

Run all three B1 test files, Ruff over every B1 path, and mypy over the three
new application modules. Capture separate stdout, stderr, exit code, duration,
test count, command, Python version, Poetry version, branch, and commit.

- [ ] **Step 2: Run compatibility and migration neighbors**

Run:

```powershell
& .\.venv\Scripts\poetry.exe run pytest -p no:cacheprovider `
  backend/tests/unit/test_lab_schema.py `
  backend/tests/unit/test_a2_science_schema.py `
  backend/tests/unit/test_a2_science_service.py `
  backend/tests/integration/test_a5_operations_migration.py `
  backend/tests/integration/test_backup_restore.py -q
```

Expected: zero failures. Restore and hash-check the canonical database and
knowledge base if any verifier touches them.

- [ ] **Step 3: Verify the B1 claim boundary**

Record:

- B1 migrated high-impact value count is exactly zero;
- synthetic accepted derivations reconstruct completely;
- legacy scientific runtime consumers are unchanged;
- no `LabEvidenceRecord` was promoted;
- no staged, parsed, or AI-generated extraction is authoritative;
- scientific release remains blocked.

- [ ] **Step 4: Write deterministic B1 reports**

The JSON report schema is `build-b1-source-provenance-gate-v1` and includes
commands, hashes, counts, migration revision, gate booleans, known limitations,
database hashes, and redacted environment metadata. The Markdown report mirrors
the JSON without secrets.

- [ ] **Step 5: Verify and commit the B1 gate**

Parse JSON, scan both reports for credential-like assignments, run
`git diff --check`, stage only B1 report files, and commit:

```powershell
git commit -m "docs: close Build B1 source provenance gate"
```

B1 passes only if all checks are green. Do not begin B2 on partial evidence.
