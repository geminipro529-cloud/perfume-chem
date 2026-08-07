# Build B5 Analytical Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task in the
> current session. Project instructions prohibit Codex subagents; bounded
> DeepLuna Fast review is advisory and Sol performs final acceptance. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a zero-backfill, append-only B5 authority path from an
immutable analytical method through validation, sequence, preserved raw data,
QC, peak identity/quantity, and a fail-closed evidence claim.

**Architecture:** Keep the existing A2 analytical tables as the acquisition
spine and add eight B5 specialization tables plus a focused service/repository
module. Only the B5 claim assessment can authorize an analytical result, and
the existing A2 exact analytical claim path must verify a matching supported
B5 assessment. No API, export-revision, optimizer, UI, or protected-database
change is in scope.

**Tech Stack:** Python 3.11, SQLAlchemy 2 async ORM, Alembic, SQLite/PostgreSQL
constraints, pytest/pytest-asyncio, Ruff, mypy, canonical SHA-256 JSON hashing.

---

## Execution constraints

- Work in the archived scratch clone first.
- Use RED tests before implementation changes.
- Do not mutate the A2 analytical schema or import/backfill any row.
- Do not modify `perfume_chem.db` or `data/perfumery_kb.db`.
- Do not change `lab-export-v3`, `lab-export-v4`, API routes, UI, or optimizer
  consumers; B9 owns those decisions.
- Preserve stdout and stderr separately, disable ANSI, and apply explicit
  command timeouts.
- Do not make intermediate commits. The authoritative B5 paths are committed
  only after the full B5 exit gate and canonical rerun pass.

## File map

**Create**

- `backend/app/models/lab_analytical.py`: B5 enums, eight ORM models, named
  constraints, and the B5 append-only table-name set.
- `backend/app/repositories/lab_analytical.py`: explicit-ID B5 reads only.
- `backend/app/services/lab_analytical.py`: typed commands, validation,
  canonical hashing, QC propagation, and claim assessment.
- `backend/alembic/versions/20260731_0009_b5_analytical_authority.py`: zero-row
  reversible migration and append-only triggers.
- `backend/tests/unit/test_b5_analytical_schema.py`: model contract and named
  constraint tests.
- `backend/tests/unit/test_b5_analytical_service.py`: focused method,
  sequence, identity, quantity, GC-O, and QC-gate tests.
- `backend/tests/integration/test_b5_analytical_migration.py`: migration,
  database constraint, trigger, parity, and zero-backfill tests.
- `backend/tests/integration/test_b5_analytical_e2e.py`: successful and
  failed-QC end-to-end chains.
- `docs/verification/b5/analytical_authority_gate.json`: machine-readable gate
  evidence, written only after PASS.
- `docs/verification/b5/analytical_authority_gate.md`: human-readable gate
  decision, written only after PASS.

**Modify**

- `backend/app/models/lab.py`: import B5 models and include the B5 table set in
  `APPEND_ONLY_TABLES`.
- `backend/app/repositories/lab.py`: compose
  `LabAnalyticalAuthorityRepositoryMixin`.
- `backend/app/services/lab_service.py`: compose
  `LabAnalyticalAuthorityServiceMixin`.
- `backend/app/services/lab_science.py`: require a matching supported B5
  assessment before an A2 exact analytical-run claim.
- `backend/tests/integration/test_lab_migration.py`: advance current head to
  `20260731_0009`.
- `backend/tests/integration/test_backup_restore.py`: advance current head to
  `20260731_0009`.

### Task 1: Prove the B5 schema contract RED

**Files:**

- Create: `backend/tests/unit/test_b5_analytical_schema.py`
- Test: `backend/app/models/lab.py`

- [ ] **Step 1: Write the failing table-set test**

```python
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES
from app.models.lab_analytical import ANALYTICAL_AUTHORITY_TABLE_NAMES


EXPECTED = {
    "lab_analytical_method_authorities",
    "lab_method_validation_records",
    "lab_analytical_sequences",
    "lab_analytical_sequence_entries",
    "lab_analytical_run_authorities",
    "lab_analytical_peak_authorities",
    "lab_gco_event_authorities",
    "lab_analytical_claim_assessments",
}


def test_b5_tables_are_canonical_and_append_only():
    assert ANALYTICAL_AUTHORITY_TABLE_NAMES == EXPECTED
    assert EXPECTED <= set(Base.metadata.tables)
    assert EXPECTED <= APPEND_ONLY_TABLES
    for name in EXPECTED:
        assert "updated_at" not in Base.metadata.tables[name].columns
```

- [ ] **Step 2: Add failing assertions for named constraints**

Assert the exact enum, one-to-one, content-hash, sequence-order,
same-sequence, raw-file-distinctness, range, and withheld-result constraint
names declared in Task 2. Also assert every index is named.

- [ ] **Step 3: Run the focused test and preserve RED output**

Run from `backend`:

```powershell
$env:NO_COLOR='1'
$env:PYTHONIOENCODING='utf-8'
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_schema.py -q
```

Expected: collection fails because `app.models.lab_analytical` does not exist.

### Task 2: Add B5 models and repository composition

**Files:**

- Create: `backend/app/models/lab_analytical.py`
- Create: `backend/app/repositories/lab_analytical.py`
- Modify: `backend/app/models/lab.py`
- Modify: `backend/app/repositories/lab.py`

- [ ] **Step 1: Define the closed vocabularies**

```python
ANALYTICAL_METHOD_AUTHORITY_STATUSES = (
    "EXPLORATORY", "VERIFIED", "VALIDATED_FOR_SCOPE", "RETIRED"
)
METHOD_VALIDATION_RESULTS = ("PASS", "FAIL", "INCOMPLETE")
ANALYTICAL_SEQUENCE_STATUSES = ("PLANNED", "ACQUIRED", "CANCELLED")
ANALYTICAL_SEQUENCE_ENTRY_ROLES = (
    "SAMPLE", "SOLVENT_BLANK", "METHOD_BLANK", "CALIBRATION_STANDARD",
    "INTERNAL_STANDARD", "SPIKE", "DUPLICATE", "REPLICATE", "QC_SAMPLE",
    "RI_STANDARD", "CONTROL",
)
ANALYTICAL_RUN_DISPOSITIONS = ("PENDING", "ACCEPTED", "QUALIFIED", "REJECTED")
ANALYTICAL_IDENTITY_AUTHORITY_STATES = (
    "CONFIRMED_AUTHENTIC_STANDARD",
    "STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM",
    "PROBABLE",
    "TENTATIVE_LIBRARY_MATCH",
    "UNRESOLVED",
    "REJECTED",
)
ANALYTICAL_STANDARD_MATCH_STATES = ("NOT_RUN", "MATCHED", "FAILED")
ANALYTICAL_QUANTITATION_STATES = (
    "NONE", "AREA_PERCENT_ONLY", "CALIBRATED_CONCENTRATION"
)
GCO_TRAINING_STATES = ("QUALIFIED", "IN_TRAINING", "UNKNOWN")
GCO_WINDOW_BASES = ("RETENTION_TIME", "RETENTION_INDEX")
ANALYTICAL_CLAIM_TYPES = ("IDENTITY", "QUANTITY")
ANALYTICAL_CLAIM_DECISIONS = (
    "SUPPORTED_FOR_SCOPE", "ADVISORY_ONLY", "WITHHELD"
)
```

- [ ] **Step 2: Add the eight ORM models**

Use `LabRecord`, named `UniqueConstraint`, `CheckConstraint`, and
`ForeignKeyConstraint` declarations. Required database invariants are:

```text
method authority: unique method_version_id; 64-char source/content digests
validation: unique (method_authority_id, intended_claim, scope_sha256)
sequence: unique sequence_key and content_sha256; entry_count >= 1
entry: unique (sequence_id, injection_order); injection_order >= 1
run authority: unique analytical_run_id; vendor/open attachment IDs differ;
               subject type is SAMPLE, STOCK_LOT, NATURAL_LOT,
               FORMULA_VERSION, BUILD_PLAN_VERSION, or BOTTLE_STREAM;
               only BOTTLE_STREAM carries a positive stream sequence
peak authority: unique analytical_peak_id; six-state and quantitation checks
GC-O authority: unique gco_event_id; end >= start; frequency in [0,1];
                exact_identity_claim = false
claim: exact analytical_run_id plus run/peak authority IDs; unique
       content_sha256; WITHHELD requires result_json IS NULL
```

Give sequence entries a unique `(id, sequence_id)` pair and bind run authority
to `(sequence_entry_id, sequence_id)` with a composite foreign key.

- [ ] **Step 3: Compose models into the canonical registry**

Import all eight classes and `ANALYTICAL_AUTHORITY_TABLE_NAMES` at the bottom
of `backend/app/models/lab.py`, then add
`*ANALYTICAL_AUTHORITY_TABLE_NAMES` to `APPEND_ONLY_TABLES`.

- [ ] **Step 4: Add explicit repository reads**

```python
class LabAnalyticalAuthorityRepositoryMixin:
    session: AsyncSession

    async def get_analytical_method_authority(
        self, record_id: str
    ) -> LabAnalyticalMethodAuthority | None:
        return await self.session.get(LabAnalyticalMethodAuthority, record_id)

    async def analytical_method_authority_for_version(
        self, method_version_id: str
    ) -> LabAnalyticalMethodAuthority | None:
        result = await self.session.execute(
            select(LabAnalyticalMethodAuthority).where(
                LabAnalyticalMethodAuthority.method_version_id
                == method_version_id
            )
        )
        return result.scalar_one_or_none()

    async def method_validation_records(
        self, method_authority_id: str
    ) -> list[LabMethodValidationRecord]:
        result = await self.session.execute(
            select(LabMethodValidationRecord)
            .where(
                LabMethodValidationRecord.method_authority_id
                == method_authority_id
            )
            .order_by(
                LabMethodValidationRecord.intended_claim,
                LabMethodValidationRecord.scope_sha256,
                LabMethodValidationRecord.id,
            )
        )
        return list(result.scalars())

    async def get_analytical_sequence(
        self, sequence_id: str
    ) -> LabAnalyticalSequence | None:
        return await self.session.get(LabAnalyticalSequence, sequence_id)

    async def analytical_sequence_entries(
        self, sequence_id: str
    ) -> list[LabAnalyticalSequenceEntry]:
        result = await self.session.execute(
            select(LabAnalyticalSequenceEntry)
            .where(LabAnalyticalSequenceEntry.sequence_id == sequence_id)
            .order_by(
                LabAnalyticalSequenceEntry.injection_order,
                LabAnalyticalSequenceEntry.id,
            )
        )
        return list(result.scalars())

    async def get_analytical_run_authority(
        self, record_id: str
    ) -> LabAnalyticalRunAuthority | None:
        return await self.session.get(LabAnalyticalRunAuthority, record_id)

    async def analytical_run_authority_for_run(
        self, run_id: str
    ) -> LabAnalyticalRunAuthority | None:
        result = await self.session.execute(
            select(LabAnalyticalRunAuthority).where(
                LabAnalyticalRunAuthority.analytical_run_id == run_id
            )
        )
        return result.scalar_one_or_none()

    async def get_analytical_peak_authority(
        self, record_id: str
    ) -> LabAnalyticalPeakAuthority | None:
        return await self.session.get(LabAnalyticalPeakAuthority, record_id)

    async def get_gco_event_authority(
        self, record_id: str
    ) -> LabGCOEventAuthority | None:
        return await self.session.get(LabGCOEventAuthority, record_id)

    async def get_analytical_claim_assessment(
        self, record_id: str
    ) -> LabAnalyticalClaimAssessment | None:
        return await self.session.get(LabAnalyticalClaimAssessment, record_id)
```

Every query orders deterministically and uses an explicit ID or exact foreign
key. Add no update, delete, or ambient-latest method.

- [ ] **Step 5: Run the schema test GREEN**

Run the Task 1 command. Expected: all schema tests pass.

### Task 3: Implement method and validation authority test-first

**Files:**

- Create: `backend/app/services/lab_analytical.py`
- Modify: `backend/app/services/lab_service.py`
- Test: `backend/tests/unit/test_b5_analytical_service.py`

- [ ] **Step 1: Write failing method input tests**

Cover:

```python
def test_method_authority_requires_every_component():
    with pytest.raises(AnalyticalAuthorityError):
        AnalyticalMethodAuthorityInput(
            method_version_id="method-v1",
            schema_version="b5-analytical-method-v1",
            status="VALIDATED_FOR_SCOPE",
            analyte_scope=("linalool",),
            instrument={},
            detector={},
            software={},
            separation={},
            acquisition={},
            sample_preparation={},
            hs_spme=None,
            standards={},
            calibration={},
            response_factors={},
            identity_criteria={},
            integration_policy={},
            qc_plan={},
            raw_data_policy={},
            source_document_version_id="source-v1",
            source_locator={"section": "1"},
        )
```

Add separate tests that complete GC-MS input passes, HS-SPME without all
fiber/conditioning/vial/mass/headspace/incubation/extraction/agitation/
desorption keys fails, and accreditation-like input is not accepted.

- [ ] **Step 2: Write failing validation-record tests**

Define `VALIDATION_CHARACTERISTIC_KEYS` exactly from B5.2 and prove missing
any one key fails. Prove `PASS` requires nonempty acceptance criteria,
measurement uncertainty, reviewer, review time, limitations tuple, and B1
source provenance.

- [ ] **Step 3: Run the focused tests RED**

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_service.py -q
```

Expected: imports or service methods are missing.

- [ ] **Step 4: Implement normalized immutable command types**

Add:

```python
class AnalyticalAuthorityError(ValueError):
    """Raised when analytical input cannot satisfy the B5 contract."""

class AnalyticalAuthorityConflictError(AnalyticalAuthorityError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
```

Define `AnalyticalMethodAuthorityInput` and `MethodValidationInput` as frozen,
slotted dataclasses with the exact fields exercised by Steps 1 and 2.
Canonicalization uses `json.dumps(value, allow_nan=False, sort_keys=True,
separators=(",", ":"))`. Tuple fields are deduplicated without reordering.
Authority-critical JSON objects accept only their documented keys.

- [ ] **Step 5: Implement service methods**

Implement `register_analytical_method_authority(self, command:
AnalyticalMethodAuthorityInput) -> LabAnalyticalMethodAuthority` and
`record_method_validation(self, command: MethodValidationInput) ->
LabMethodValidationRecord`.

The first method verifies the A2 method, technique-specific shape, status
compatibility, exact B1 source and artifact digest, and accepted source scope
for verified/validated states. The second verifies matching method/source,
full characteristics, scope hash, and review. Both hash every authority input.

- [ ] **Step 6: Compose the service and run focused tests GREEN**

Import `LabAnalyticalAuthorityServiceMixin` in
`backend/app/services/lab_service.py` and place it before
`LabScienceServiceMixin` in `LabService` bases. Run the Task 3 test command.

### Task 4: Implement atomic sequence and run/raw authority test-first

**Files:**

- Modify: `backend/app/services/lab_analytical.py`
- Test: `backend/tests/unit/test_b5_analytical_service.py`

- [ ] **Step 1: Write failing sequence tests**

Define:

```python
@dataclass(frozen=True, slots=True)
class AnalyticalSequenceEntryInput:
    injection_order: int
    role: str
    reference: str
    level: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class AnalyticalSequenceInput:
    sequence_key: str
    method_authority_id: str
    instrument_identifier: str
    status: str
    entries: tuple[AnalyticalSequenceEntryInput, ...]
```

Tests require contiguous positive unique order, one `SAMPLE`, method-required
QC roles, calibration standard for quantitative methods, atomic rollback on
an invalid entry, and deterministic sequence hashing.

- [ ] **Step 2: Implement `create_analytical_sequence`**

Create the header and all entries in one `_transaction()`. Compute the header
hash from the complete normalized ordered entry payload before insertion.

- [ ] **Step 3: Write failing run-authority tests**

Prove rejection for:

- a sample/formula/build-plan/bottle-stream primary subject that does not
  match its corresponding A2 contextual link;
- a missing canonical subject;
- a stock lot without a supplier lot number;
- a natural lot without both a supplier lot number and explicit
  `source_json["material_kind"] == "NATURAL"`;
- a bottle stream without an exact positive existing stream sequence;
- a non-sample or wrong-sequence entry;
- a sequence not in `ACQUIRED`;
- missing, same-ID, wrong-run, wrong-kind, or malformed-digest attachments;
- missing instrument state, applicability, review, or disposition detail.

- [ ] **Step 4: Implement `bind_analytical_run_authority`**

Implement `bind_analytical_run_authority(self, command:
AnalyticalRunAuthorityInput) -> LabAnalyticalRunAuthority`.

Require attachment kinds exactly `RAW_VENDOR_DATA` and `OPEN_EXPORT`, verify
both A2 attachment FKs and digests, and copy all upstream content hashes into
the run-authority hash payload. Resolve the one primary subject by
`subject_type`; keep any additional A2 subject links as context only and never
include them in claim applicability.

- [ ] **Step 5: Run sequence/run tests GREEN**

Run only tests selected with:

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_service.py -q -k "sequence or run_authority or raw"
```

Expected: selected tests pass.

### Task 5: Implement peak and GC-O authority test-first

**Files:**

- Modify: `backend/app/services/lab_analytical.py`
- Test: `backend/tests/unit/test_b5_analytical_service.py`

- [ ] **Step 1: Write failing six-state identity tests**

Parameterize all six states. Add explicit cases proving:

- library match alone cannot exceed `TENTATIVE_LIBRARY_MATCH`;
- `STRONGLY_SUPPORTED_RI_PLUS_SPECTRUM` requires both RI and spectrum;
- `CONFIRMED_AUTHENTIC_STANDARD` requires matched authentic standard or
  co-injection, material ID, retention evidence, spectrum, and manual review;
- unresolved/rejected states cannot expose an authoritative identity result.

- [ ] **Step 2: Write failing quantitation tests**

Prove `CALIBRATED_CONCENTRATION` requires calibration reference, standard,
response factor, working range, dilution, blank correction, applicable QC,
quantity/basis/unit, and uncertainty. Prove `AREA_PERCENT_ONLY` cannot request
weight-percent or bulk concentration. Prove HS-SPME concentration fails unless
matrix, analyte, and method calibration IDs match the method/run/peak scope.

- [ ] **Step 3: Implement `record_analytical_peak_authority`**

Implement `record_analytical_peak_authority(self, command:
AnalyticalPeakAuthorityInput) -> LabAnalyticalPeakAuthority`.

Fetch the A2 peak, run authority, method authority, method validation, and QC
records by explicit ID. Enforce identity ceilings before quantitation rules.

- [ ] **Step 4: Write failing GC-O tests**

Require training, coherent RT/RI window, detection method, replicate index and
count, frequency in `[0, 1]`, repeatability, and same-run aligned peaks.
Attempting `exact_identity_claim=True` must fail in both the command and direct
database constraint tests.

- [ ] **Step 5: Implement `record_gco_event_authority`**

Implement `record_gco_event_authority(self, command: GCOEventAuthorityInput)
-> LabGCOEventAuthority`.

Verify the A2 event, its run, every aligned A2 peak, and window basis. Persist
`exact_identity_claim=False` unconditionally.

- [ ] **Step 6: Run peak/GC-O tests GREEN**

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_service.py -q -k "identity or quantitation or hs_spme or gco"
```

Expected: selected tests pass.

### Task 6: Implement QC propagation and close the exact-claim bypass

**Files:**

- Modify: `backend/app/services/lab_analytical.py`
- Modify: `backend/app/services/lab_science.py`
- Test: `backend/tests/unit/test_b5_analytical_service.py`
- Test: `backend/tests/integration/test_b5_analytical_e2e.py`

- [ ] **Step 1: Freeze missing and qualification codes**

```python
ANALYTICAL_MISSING_REQUIREMENT_CODES = (
    "METHOD_AUTHORITY_MISSING",
    "METHOD_STATUS_INSUFFICIENT",
    "METHOD_VALIDATION_MISSING",
    "METHOD_VALIDATION_FAILED",
    "SEQUENCE_NOT_ACQUIRED",
    "RAW_VENDOR_DATA_MISSING",
    "OPEN_EXPORT_MISSING",
    "RUN_DISPOSITION_BLOCKING",
    "QC_REQUIRED_CHECK_MISSING",
    "QC_REQUIRED_CHECK_UNRESOLVED",
    "QC_FAILED_BLOCKING",
    "IDENTITY_EVIDENCE_INSUFFICIENT",
    "CALIBRATION_MISSING",
    "QUANTITATION_BASIS_INVALID",
    "UNCERTAINTY_MISSING",
    "APPLICABILITY_MISMATCH",
    "REVIEW_MISSING",
)
ANALYTICAL_QUALIFICATION_CODES = ("QC_FAILED_QUALIFYING",)
```

- [ ] **Step 2: Write failing claim-gate tests**

For each missing dimension, call `assess_analytical_claim` and assert the exact
sorted code tuple. Assert a withheld assessment has `result_json is None`.
Assert a `BLOCK` QC failure withholds and a `QUALIFY` failure caps at
`ADVISORY_ONLY`.

- [ ] **Step 3: Implement deterministic QC evaluation**

```python
@dataclass(frozen=True, slots=True)
class AnalyticalGateResult:
    decision: str
    missing_requirements: tuple[str, ...]
    qualifications: tuple[str, ...]
    details: Mapping[str, Any]
    result: Mapping[str, Any] | None
```

Group A2 QC rows by normalized `qc_type`, apply the exact method
`required_checks` and `failure_policy`, then sort codes and detail keys.

- [ ] **Step 4: Implement and persist the assessment**

Implement `assess_analytical_claim(self, command: AnalyticalClaimRequest) ->
LabAnalyticalClaimAssessment`.

Evaluate method, validation, sequence, run, raw files, QC, peak,
identity/quantity, uncertainty, applicability, and review. Hash upstream B5
records and the final gate result. Persist even withheld/advisory decisions so
the reason is auditable.

- [ ] **Step 5: Close the A2 legacy bypass**

In the existing `ALLOW_EXACT` + `ANALYTICAL_RUN` branch, require:

```python
assessment_id = command.authority.get("analytical_authority_assessment_id")
assessment = await self.repository.get_analytical_claim_assessment(
    str(assessment_id)
)
if (
    assessment is None
    or assessment.analytical_run_id != command.subject_id
    or assessment.decision != "SUPPORTED_FOR_SCOPE"
):
    raise ScienceAuthorityConflictError(
        "ANALYTICAL_B5_AUTHORITY_REQUIRED",
        "Exact analytical authority requires a matching supported B5 assessment.",
    )
```

Retain the existing direct evidence and review checks. Do not alter
non-analytical claims.

- [ ] **Step 6: Prove legacy all-PASS QC no longer bypasses B5**

Create an A2 run with all PASS QC and no B5 assessment. Assert
`ANALYTICAL_B5_AUTHORITY_REQUIRED`. Then create the complete B5 chain, pass its
assessment ID, and assert the scoped exact A2 claim can be persisted.

- [ ] **Step 7: Run focused claim tests GREEN**

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_service.py tests/integration/test_b5_analytical_e2e.py -q -k "claim or qc or bypass"
```

Expected: selected tests pass.

### Task 7: Add the reversible zero-backfill migration test-first

**Files:**

- Create: `backend/tests/integration/test_b5_analytical_migration.py`
- Create: `backend/alembic/versions/20260731_0009_b5_analytical_authority.py`
- Modify: `backend/tests/integration/test_lab_migration.py`
- Modify: `backend/tests/integration/test_backup_restore.py`

- [ ] **Step 1: Write migration tests RED**

Test:

- upgrade from `20260731_0008` to `20260731_0009`;
- all eight tables exist and contain zero rows;
- existing B1-B4 and A2 row counts/hashes are unchanged;
- every B5 table rejects UPDATE and DELETE on SQLite;
- direct invalid enum/range/raw-file/GC-O/withheld-result inserts fail;
- model/migration columns, named constraints, named indexes, and FKs match;
- downgrade removes only B5 tables and returns to `20260731_0008`;
- re-upgrade succeeds with zero B5 rows.

- [ ] **Step 2: Run migration tests RED**

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/integration/test_b5_analytical_migration.py -q
```

Expected: migration revision is missing.

- [ ] **Step 3: Implement revision `20260731_0009`**

Set:

```python
revision = "20260731_0009"
down_revision = "20260731_0008"
```

Create tables in dependency order, named indexes explicitly, and SQLite
append-only triggers with the repository's established dialect guards.
Create no authority data.

- [ ] **Step 4: Advance current-head assertions**

Change only:

```python
CURRENT_HEAD = "20260731_0009"
```

in `test_lab_migration.py` and `test_backup_restore.py`.

- [ ] **Step 5: Run migration tests GREEN**

Run:

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/integration/test_b5_analytical_migration.py tests/integration/test_lab_migration.py tests/integration/test_backup_restore.py -q
```

Expected: all selected migration and backup/restore tests pass.

### Task 8: Prove both B5 end-to-end outcomes

**Files:**

- Create: `backend/tests/integration/test_b5_analytical_e2e.py`
- Modify: `backend/tests/unit/test_b5_analytical_service.py`

- [ ] **Step 1: Build one complete supported identity/quantity fixture**

The fixture must create:

```text
accepted B1 source
-> A2 GC-MS method
-> B5 VALIDATED_FOR_SCOPE method
-> PASS method validation
-> acquired sequence with blank/calibration/internal-standard/RI/QC/sample
-> A2 run plus one exact B5 primary formula-version subject
-> RAW_VENDOR_DATA + OPEN_EXPORT attachments
-> B5 accepted run authority
-> all required PASS QC
-> A2 peak
-> B5 CONFIRMED_AUTHENTIC_STANDARD + CALIBRATED_CONCENTRATION peak
-> B5 SUPPORTED_FOR_SCOPE claim
-> A2 exact analytical claim carrying the B5 assessment ID
```

Assert every FK and upstream hash in the assessment resolves to the exact
created record.

- [ ] **Step 2: Build the failed-QC twin**

Copy the fixture inputs into a separate immutable graph, change the required
blank QC to `FAIL`, and assert:

```python
assert assessment.decision == "WITHHELD"
assert assessment.missing_requirements_json == ["QC_FAILED_BLOCKING"]
assert assessment.result_json is None
```

Also assert the A2 exact claim rejects that assessment.

- [ ] **Step 3: Add a qualifying-QC twin**

Declare the selected method policy `QUALIFY` for duplicate failure. Assert the
assessment is `ADVISORY_ONLY`, includes `QC_FAILED_QUALIFYING`, and cannot
authorize an A2 exact claim.

- [ ] **Step 4: Run the complete focused B5 suite**

```powershell
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m pytest tests/unit/test_b5_analytical_schema.py tests/unit/test_b5_analytical_service.py tests/integration/test_b5_analytical_migration.py tests/integration/test_b5_analytical_e2e.py -q
```

Expected: all B5 tests pass.

### Task 9: Verify, promote, audit, and report

**Files:**

- Create after PASS:
  `docs/verification/b5/analytical_authority_gate.json`
- Create after PASS:
  `docs/verification/b5/analytical_authority_gate.md`
- Promote only the exact B5 file map above.

- [ ] **Step 1: Run the B1-B5 compatibility slice in scratch**

Include B1 source, B2 property, B3 threshold/OAV, B4 rules, all A2 science
tests, all B5 tests, current migration, and backup/restore tests. Use an
explicit 15-minute timeout and separate stdout/stderr files.

- [ ] **Step 2: Run static checks in scratch**

```powershell
D:\chatbots\perfume-chem\.venv\Scripts\ruff.exe check --no-cache --output-format concise app/models/lab_analytical.py app/repositories/lab_analytical.py app/services/lab_analytical.py app/models/lab.py app/repositories/lab.py app/services/lab_service.py app/services/lab_science.py alembic/versions/20260731_0009_b5_analytical_authority.py tests/unit/test_b5_analytical_schema.py tests/unit/test_b5_analytical_service.py tests/integration/test_b5_analytical_migration.py tests/integration/test_b5_analytical_e2e.py tests/integration/test_lab_migration.py tests/integration/test_backup_restore.py
D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe -m mypy app/models/lab_analytical.py app/repositories/lab_analytical.py app/services/lab_analytical.py
```

Expected: zero exit status and empty stderr.

- [ ] **Step 3: Reproduce migration and protected-data invariants**

Run an empty-database upgrade, B4-to-B5 upgrade, B5 downgrade, and re-upgrade.
Hash `perfume_chem.db` and `data/perfumery_kb.db` before and after. Open the
protected knowledge DB only with SQLite immutable read-only mode and require
`PRAGMA integrity_check = ok`.

- [ ] **Step 4: Archive the canonical targets before promotion**

Create a new path-preserving ZIP, extract it, compare every restored SHA-256,
and record absent paths. Stop if any existing target cannot be restored.

- [ ] **Step 5: Promote exact files and verify hashes**

Copy only the frozen B5 file map from scratch to the authoritative repository.
Compare every source/destination SHA-256. Do not clean or reset unrelated
tracked or untracked work.

- [ ] **Step 6: Rerun all Task 9 checks canonically**

Preserve command, cwd, interpreter, timeout, exit code, duration, stdout hash,
stderr hash, and exact test count.

- [ ] **Step 7: Run fresh DeepLuna Fast post-implementation audit**

Immediately before submission, run exact-project `deepseek_check`. Submit only
if status is `READY`, using `FLASH`/Fast-only and no Luna/Codex fallback.
Bound the audit to B5 changed paths and exit criteria. Sol must independently
reproduce every reported finding and fix/retest any confirmed defect.

- [ ] **Step 8: Write gate reports only after all checks pass**

The JSON and Markdown reports record baseline/archive hashes, migration head,
test counts, commands and log digests, protected database hashes, DeepLuna job
and bounded result, Sol reproduction, residual limitations, and the exact B5
PASS decision.

- [ ] **Step 9: Commit only exact B5 paths**

Verify an empty index first, stage the exact B5 paths, inspect
`git diff --cached --name-status`, commit once, and confirm no unrelated path
was staged. Do not begin B6 until the B5 boundary report is complete.
