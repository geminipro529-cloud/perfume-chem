# A2 Slice 1 Canonical Planning Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Repository
> policy prohibits Codex subagents; Sol remains the sole head engineer and
> final approver.

**Goal:** Add the first A2 vertical slice: append-oriented canonical
persistence for target hypotheses, target acceptance, formula-version
lineage, inventory mapping, immutable build-plan versions and lines, and
transactional stock reservations.

**Architecture:** Extend the accepted `lab_*` SQLAlchemy/Alembic authority
without promoting engine dataclasses or legacy tables. New focused planning
models are aggregated through `app.models.lab`; ordinary commands continue to
flow through `LabService` and `LabRepository`; a new `/lab/v2` router remains
thin. All schema work is tested on empty and representative database copies in
this slice. The zero-byte canonical `perfume_chem.db` is not migrated until
the later A2 migration-acceptance slice.

**Tech Stack:** Python 3.11, SQLAlchemy 2, Alembic, aiosqlite, FastAPI,
Pydantic v2, pytest/pytest-asyncio, Ruff, MyPy, SQLite.

---

Status: implementation not started

Starting implementation checkpoint:
`c52e4933aa0ee7a9d79f6f595cf3d3e1b7973049`

Required predecessor gate: A1R `PASS_WITH_SKIPS`

Protected pre-plan recovery package:
`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-plan-preedit-recovery\perfume-chem-a0-20260729T191929Z`

## Scope boundary

This plan covers only the first of four approved A2 slices:

1. target, acceptance, formula-DAG, inventory-mapping, build-plan, build-line,
   and reservation persistence.

It does not implement:

- analytical method/run/peak/QC/attachment persistence;
- regulatory assessments or claim-specific authority decisions;
- one-way adapters or closure of legacy write paths;
- bottle-action proposal/confirmation APIs;
- canonical database migration;
- A2 completion or permission to begin A3.

The slice ends at an A2.1 checkpoint and user review. A2 Slice 2 remains
prohibited until that checkpoint is accepted.

## Locked file map

### Create

- `backend/app/models/lab_planning.py` — focused A2 planning ORM entities.
- `backend/app/repositories/lab_planning.py` — planning query mixin; no
  transaction ownership.
- `backend/app/services/lab_planning.py` — immutable command DTOs, transitions,
  hashes, and planning service mixin.
- `backend/app/schemas/lab_planning.py` — versioned API request/response
  contracts and stable error envelope.
- `backend/app/api/v1/endpoints/lab_planning.py` — thin `/lab/v2` planning
  routes.
- `backend/alembic/versions/20260730_0001_a2_planning_core.py` — frozen,
  explicit migration from `20260717_0001`.
- `backend/tests/unit/test_a2_planning_schema.py` — model/table/constraint
  contracts.
- `backend/tests/a2_planning_fixtures.py` — complete reusable target, stock,
  mapping, accepted-plan, and reservation graph fixtures for new tests only.
- `backend/tests/unit/test_a2_planning_service.py` — target, acceptance,
  lineage, mapping, build-plan, and transition contracts.
- `backend/tests/integration/test_a2_planning_migration.py` — empty/current
  upgrade, one-head, downgrade, backup, legacy preservation, trigger, FK, and
  constraint contracts.
- `backend/tests/integration/test_a2_planning_transactions.py` — atomic
  reservation and concurrency contracts.
- `backend/tests/integration/test_a2_planning_export.py` — v1 import
  compatibility and deterministic v2 round-trip.
- `backend/tests/integration/test_a2_planning_api.py` — versioned API and
  stable error-code contracts.

### Modify

- `backend/app/models/lab.py` — import focused planning entities before
  computing `LAB_TABLE_NAMES`; add their immutable tables to
  `APPEND_ONLY_TABLES`.
- `backend/app/repositories/lab.py` — compose the planning query mixin into
  `LabRepository`.
- `backend/app/services/lab_service.py` — compose the planning command mixin
  into `LabService`; retain its existing transaction owner.
- `backend/app/services/lab_export.py` — export format v2, dependency order,
  deterministic ordering, and v1 import compatibility.
- `backend/app/api/v1/router.py` — mount the new focused router at `/lab/v2`;
  do not edit the user-modified `endpoints/lab.py`.
- `backend/tests/unit/test_lab_schema.py` — require every new append-only table
  to omit mutable timestamp columns.
- `backend/tests/integration/test_backup_restore.py` — require backup manifests
  to bind the new single Alembic head.
- `docs/verification/a2_slice1/README.md` — commands, hashes, migration-copy
  evidence, known skips, and the explicit statement that the canonical
  database was not migrated.

### Explicitly protected from this slice

- `backend/app/api/v1/endpoints/lab.py`
- `backend/app/schemas/lab.py`
- `backend/tests/integration/test_lab_api.py`
- `perfume_chem.db`
- every legacy table and historical migration file

## Canonical planning schema contract

The migration and ORM must declare these immutable records:

| Table | Purpose | Required database contracts |
|---|---|---|
| `lab_target_hypothesis_versions` | Stable target plus immutable versions | unique `(target_id, version_number)` and `content_sha256`; parent FK; version `>= 1` |
| `lab_target_lines` | Ordered identity/quantity rows independent of stock | unique `(target_version_id, position)`, `(target_version_id, line_id)`, and `(id, target_version_id)`; nonnegative quantities; fractions/probabilities in `[0,1]` |
| `lab_target_evidence_links` | FK-backed target or target-line evidence links | unique `(target_version_id, target_line_id, evidence_record_id)`; composite FK proves the line belongs to the target version |
| `lab_accepted_target_versions` | Reviewed acceptance of one immutable target version | unique target-version FK; unique `(accepted_target_id, version_number)`; reviewer/rationale/hash required |
| `lab_formula_version_edges` | Canonical parent/change edge for existing formula versions | unique `(child_version_id, parent_version_id)`; child differs from parent |
| `lab_inventory_mapping_versions` | Versioned target-line to physical-stock decision | unique `(mapping_id, version_number)`; nullable stock only for explicit unavailable status; confidence in `[0,1]` |
| `lab_inventory_mapping_evidence_links` | FK-backed mapping evidence links | unique `(mapping_version_id, evidence_record_id)` |
| `lab_build_plan_versions` | Stable plan plus immutable status-bearing versions | unique `(plan_id, version_number)` and `content_sha256`; target/acceptance refs; status check; parent FK |
| `lab_build_plan_lines` | Complete immutable physical execution rows | unique `(build_plan_version_id, position)`, `(build_plan_version_id, line_id)`, and `(id, build_plan_version_id)`; positive measurable resolution; nonnegative quantities/loss |
| `lab_build_plan_evidence_links` | FK-backed plan or plan-line evidence links | unique `(build_plan_version_id, build_plan_line_id, evidence_record_id)`; composite FK proves the line belongs to the plan version |
| `lab_inventory_reservation_events` | Append-only reservation state stream | unique `(reservation_id, sequence)` and `idempotency_key`; sequence `>=1`; reserved mass `>0`; parent-event FK |

Allowed build-plan statuses are exactly:

```python
BUILD_PLAN_TRANSITIONS = {
    "DRAFT": {"UNDER_REVIEW", "CANCELLED", "SUPERSEDED"},
    "UNDER_REVIEW": {"APPROVED", "DRAFT", "CANCELLED", "SUPERSEDED"},
    "APPROVED": {"RESERVED", "CANCELLED", "SUPERSEDED"},
    "RESERVED": {"EXECUTING", "CANCELLED", "SUPERSEDED"},
    "EXECUTING": {"CLOSED", "CANCELLED"},
    "CLOSED": set(),
    "SUPERSEDED": set(),
    "CANCELLED": set(),
}
```

Allowed reservation transitions are exactly:

```python
RESERVATION_TRANSITIONS = {
    "RESERVED": {"RELEASED", "FULFILLED", "CANCELLED"},
    "RELEASED": set(),
    "FULFILLED": set(),
    "CANCELLED": set(),
}
```

Every change in plan or reservation state creates a new immutable version or
event. No service method updates or deletes these rows.

### Build-plan version fields

`LabBuildPlanVersion` must contain:

```python
id: str                         # immutable version ID from LabRecord
plan_id: str                    # stable plan ID
version_number: int
schema_version: str
target_hypothesis_version_id: str
accepted_target_version_id: str
parent_version_id: str | None
status: str
author: str
reviewer: str | None
reviewed_at: datetime | None
provenance_activity_json: dict
inventory_snapshot_ref: str
content_sha256: str
parent_sha256: str | None
uncertainty_summary_json: dict
rationale: str
created_at: datetime
```

`LabBuildPlanLine` must contain:

```python
id: str
line_id: str
build_plan_version_id: str
position: int
target_line_id: str
target_identity: str
inventory_mapping_version_id: str
stock_solution_id: str
planned_raw_quantity: float
planned_active_quantity: float
unit: str
concentration_fraction: float
concentration_basis: str
density_g_ml: float | None
density_source: str | None
standard_uncertainty: float | None
measurement_method: str
resolution: float
expected_transfer_loss: float
substitution_class: str
preserved_functions_json: list[str]
lost_functions_json: list[str]
rationale: str
reservation_state: str
execution_state: str
created_at: datetime
```

The remaining entity fields are fixed as:

```python
class LabTargetHypothesisVersion:
    id: str
    target_id: str
    version_number: int
    schema_version: str
    product_key: str
    parent_version_id: str | None
    author: str
    provenance_activity_json: dict
    uncertainty_summary_json: dict
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class LabTargetLine:
    id: str
    line_id: str
    target_hypothesis_version_id: str
    position: int
    target_identity: str
    source_name: str
    grade: str
    presence_probability: float
    target_raw_quantity: float
    target_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    functional_roles_json: list[str]
    uncertainty_json: dict
    created_at: datetime


class LabTargetEvidenceLink:
    id: str
    target_hypothesis_version_id: str
    target_line_id: str | None
    evidence_record_id: str
    created_at: datetime


class LabAcceptedTargetVersion:
    id: str
    accepted_target_id: str
    version_number: int
    target_hypothesis_version_id: str
    parent_version_id: str | None
    reviewer: str
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class LabFormulaVersionEdge:
    id: str
    child_version_id: str
    parent_version_id: str
    relationship_kind: str
    change_json: dict
    rationale: str
    content_sha256: str
    created_at: datetime


class LabInventoryMappingVersion:
    id: str
    mapping_id: str
    version_number: int
    parent_version_id: str | None
    target_line_id: str
    stock_solution_id: str | None
    target_identity: str
    build_identity: str
    identity_status: str
    inventory_status: str
    substitution_class: str
    preserved_functions_json: list[str]
    lost_functions_json: list[str]
    confidence: float
    rationale: str
    content_sha256: str
    parent_sha256: str | None
    created_at: datetime


class LabInventoryMappingEvidenceLink:
    id: str
    inventory_mapping_version_id: str
    evidence_record_id: str
    created_at: datetime


class LabBuildPlanEvidenceLink:
    id: str
    build_plan_version_id: str
    build_plan_line_id: str | None
    evidence_record_id: str
    created_at: datetime


class LabInventoryReservationEvent:
    id: str
    reservation_id: str
    sequence: int
    parent_event_id: str | None
    build_plan_version_id: str
    build_plan_line_id: str
    stock_solution_id: str
    state: str
    reserved_mass_g: float
    idempotency_key: str
    command_sha256: str
    actor: str
    rationale: str
    created_at: datetime
```

## Task 1: Reconfirm the protected boundary

**Files:**

- Read:
  `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-plan-preedit-recovery\perfume-chem-a0-20260729T191929Z\recovery_summary.json`
- Read: `perfume_chem.db`
- Read: `data/perfumery_kb.db`
- Read: `backend/alembic/versions/`

- [ ] **Step 1: Run a fresh exact-project DeepLuna readiness check**

Run `deepseek_check` from the `D:\chatbots\perfume-chem` task context.

Expected: `READY`, accepted runtime and ACL, provider enabled, no unknown
reservation, and sufficient read capacity. If it is not `READY`, perform no
provider transmission and continue with deterministic local checks.

- [ ] **Step 2: Verify the pre-plan recovery package**

Run:

```powershell
$summary = Get-Content -Raw -LiteralPath `
  'C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a2-plan-preedit-recovery\perfume-chem-a0-20260729T191929Z\recovery_summary.json' |
  ConvertFrom-Json
if ($summary.head -ne 'c52e4933aa0ee7a9d79f6f595cf3d3e1b7973049') {
  throw 'A2 plan archive is bound to the wrong checkpoint.'
}
if (-not $summary.restoration_verified) {
  throw 'A2 plan archive was not restoration verified.'
}
if ($summary.source_changed_during_archive_count -ne 0) {
  throw 'Repository changed while the A2 plan archive was captured.'
}
```

Expected: exit 0. Do not print sensitive-path lists or archive contents.

- [ ] **Step 3: Verify the implementation start and database bytes**

Run:

```powershell
if ((git rev-parse HEAD).Trim() -ne
    'c52e4933aa0ee7a9d79f6f595cf3d3e1b7973049') {
  throw 'A2.1 must start from the accepted A1R checkpoint.'
}
$canonical = Get-FileHash -Algorithm SHA256 -LiteralPath 'perfume_chem.db'
$knowledge = Get-FileHash -Algorithm SHA256 -LiteralPath 'data\perfumery_kb.db'
if ($canonical.Hash.ToLowerInvariant() -ne
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855') {
  throw 'Canonical database no longer matches the zero-byte A1R baseline.'
}
if ($knowledge.Hash.ToLowerInvariant() -ne
    '5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1') {
  throw 'Knowledge database no longer matches the restored A1R baseline.'
}
```

Expected: exit 0.

- [ ] **Step 4: Prove the Alembic chain has one current head**

Run from `backend`:

```powershell
poetry run alembic heads
poetry run alembic history
```

Expected: one head, `20260717_0001`, whose parent is `20260716_0001`.

## Task 2: Write the RED schema and migration contracts

**Files:**

- Create: `backend/tests/unit/test_a2_planning_schema.py`
- Create: `backend/tests/integration/test_a2_planning_migration.py`
- Modify: `backend/tests/unit/test_lab_schema.py`

- [ ] **Step 1: Add the metadata contract**

Create the following test:

```python
from sqlalchemy import CheckConstraint, UniqueConstraint

import app.models.lab  # noqa: F401
from app.models.base import Base
from app.models.lab import APPEND_ONLY_TABLES


PLANNING_TABLES = {
    "lab_target_hypothesis_versions",
    "lab_target_lines",
    "lab_target_evidence_links",
    "lab_accepted_target_versions",
    "lab_formula_version_edges",
    "lab_inventory_mapping_versions",
    "lab_inventory_mapping_evidence_links",
    "lab_build_plan_versions",
    "lab_build_plan_lines",
    "lab_build_plan_evidence_links",
    "lab_inventory_reservation_events",
}


def test_a2_planning_tables_are_canonical_and_append_only():
    assert PLANNING_TABLES <= set(Base.metadata.tables)
    assert PLANNING_TABLES <= APPEND_ONLY_TABLES
    for name in PLANNING_TABLES:
        assert "updated_at" not in Base.metadata.tables[name].columns


def test_a2_planning_tables_declare_named_checks_and_uniqueness():
    expected = {
        "lab_target_hypothesis_versions": {
            "uq_lab_target_version",
            "ck_lab_target_version_positive",
        },
        "lab_target_lines": {
            "uq_lab_target_line_position",
            "uq_lab_target_line_identity",
            "uq_lab_target_line_id_version",
            "ck_lab_target_line_quantities",
            "ck_lab_target_line_fractions",
        },
        "lab_target_evidence_links": {
            "uq_lab_target_evidence_link",
        },
        "lab_inventory_mapping_evidence_links": {
            "uq_lab_mapping_evidence_link",
        },
        "lab_build_plan_versions": {
            "uq_lab_build_plan_version",
            "ck_lab_build_plan_status",
        },
        "lab_build_plan_lines": {
            "uq_lab_build_plan_line_position",
            "uq_lab_build_plan_line_identity",
            "uq_lab_build_plan_line_id_version",
            "ck_lab_build_plan_line_quantities",
        },
        "lab_build_plan_evidence_links": {
            "uq_lab_build_plan_evidence_link",
        },
        "lab_inventory_reservation_events": {
            "uq_lab_reservation_sequence",
            "uq_lab_reservation_idempotency",
            "ck_lab_reservation_sequence",
            "ck_lab_reservation_mass",
            "ck_lab_reservation_state",
        },
    }
    for table_name, required in expected.items():
        constraints = {
            constraint.name
            for constraint in Base.metadata.tables[table_name].constraints
            if isinstance(constraint, (CheckConstraint, UniqueConstraint))
        }
        assert required <= constraints
```

- [ ] **Step 2: Add empty/current/rollback migration contracts**

Create `test_a2_planning_migration.py` with a local Alembic config helper and
these tests:

```python
def test_a2_planning_migration_upgrades_empty_database(tmp_path):
    database = tmp_path / "empty.db"
    command.upgrade(_config(database), "head")
    assert _revision(database) == "20260730_0001"
    assert PLANNING_TABLES <= _tables(database)
    assert _integrity(database) == "ok"


def test_a2_planning_migration_upgrades_released_schema_copy(tmp_path):
    database = tmp_path / "released.db"
    config = _config(database)
    command.upgrade(config, "20260717_0001")
    _insert_representative_lab_rows(database)
    before = _representative_rows(database)
    command.upgrade(config, "head")
    assert _representative_rows(database) == before
    assert _revision(database) == "20260730_0001"


def test_a2_planning_migration_downgrades_to_released_head(tmp_path):
    database = tmp_path / "rollback.db"
    config = _config(database)
    command.upgrade(config, "head")
    command.downgrade(config, "20260717_0001")
    assert not (PLANNING_TABLES & _tables(database))
    assert _revision(database) == "20260717_0001"
    assert _integrity(database) == "ok"


def test_a2_planning_migration_preserves_legacy_tables(tmp_path):
    database = tmp_path / "legacy.db"
    _create_legacy_material(database, "legacy orris")
    command.upgrade(_config(database), "head")
    assert _legacy_material(database) == "legacy orris"
```

The helper must use `sqlite3`, `alembic.command`, and a test-local `Config`;
it must not open the repository's canonical database.

- [ ] **Step 3: Add database-enforced immutable and constraint contracts**

Add tests that:

- insert a minimum valid row for every new table;
- reject `UPDATE` and `DELETE` with an `append-only` integrity error;
- reject a target line with negative quantity or probability outside `[0,1]`;
- reject a build line with zero resolution or negative transfer loss;
- reject a reservation with zero mass, sequence zero, duplicate
  `(reservation_id, sequence)`, or duplicate idempotency key;
- reject a formula edge whose child equals its parent;
- reject missing target, acceptance, formula, stock, mapping, build-plan, and
  parent-event foreign keys with `PRAGMA foreign_keys=ON`.

- [ ] **Step 4: Run the schema and migration tests to observe RED**

Run:

```powershell
poetry run pytest `
  tests/unit/test_a2_planning_schema.py `
  tests/integration/test_a2_planning_migration.py `
  -q --disable-warnings --color=no
```

Expected: failure because the eleven planning tables and
`20260730_0001` do not exist. If the tests pass before implementation, stop
because the RED contract is invalid.

## Task 3: Implement the focused ORM and explicit migration

**Files:**

- Create: `backend/app/models/lab_planning.py`
- Create:
  `backend/alembic/versions/20260730_0001_a2_planning_core.py`
- Modify: `backend/app/models/lab.py`

- [ ] **Step 1: Add all planning ORM entities**

Use `LabRecord`, `UTCDateTime`, named SQLAlchemy constraints, explicit
`ondelete="RESTRICT"` foreign keys, JSON defaults, and no relationship-driven
cascade. All quantity fields are `Float`; every quantity carries an explicit
unit/basis field. Every table is append-only.

The model module must export:

```python
__all__ = [
    "LabAcceptedTargetVersion",
    "LabBuildPlanEvidenceLink",
    "LabBuildPlanLine",
    "LabBuildPlanVersion",
    "LabFormulaVersionEdge",
    "LabInventoryMappingEvidenceLink",
    "LabInventoryMappingVersion",
    "LabInventoryReservationEvent",
    "LabTargetEvidenceLink",
    "LabTargetHypothesisVersion",
    "LabTargetLine",
    "PLANNING_TABLE_NAMES",
]
```

Add the model-status constants exactly as declared in this plan. Do not use
SQLAlchemy enums; named string checks keep SQLite migrations explicit and
portable.

- [ ] **Step 2: Aggregate planning models through the canonical module**

At the end of `backend/app/models/lab.py`, before `LAB_TABLE_NAMES` is
computed, import every planning model. Extend `APPEND_ONLY_TABLES` with all
eleven table names. Keep `LAB_TABLE_NAMES` derived from `Base.metadata`.

This ensures `import app.models.lab`, Alembic metadata, tests, export/import,
and existing callers all observe one canonical model graph.

- [ ] **Step 3: Write a frozen explicit migration**

Set:

```python
revision = "20260730_0001"
down_revision = "20260717_0001"
branch_labels = None
depends_on = None
```

The migration must:

1. call `op.create_table` in FK dependency order;
2. name every check, unique constraint, foreign key, and index;
3. install SQLite `BEFORE UPDATE` and `BEFORE DELETE` append-only triggers for
   every new table;
4. drop triggers and tables in reverse dependency order in `downgrade`;
5. contain no import from `app.models`, no `Base.metadata`, no `checkfirst`,
   and no conditional table skip.

- [ ] **Step 4: Run the RED tests to GREEN**

Run:

```powershell
poetry run pytest `
  tests/unit/test_a2_planning_schema.py `
  tests/unit/test_lab_schema.py `
  tests/integration/test_a2_planning_migration.py `
  -q --disable-warnings --color=no
```

Expected: all selected tests pass.

- [ ] **Step 5: Run static checks for the slice**

Run:

```powershell
poetry run ruff check `
  app/models/lab.py `
  app/models/lab_planning.py `
  alembic/versions/20260730_0001_a2_planning_core.py `
  tests/unit/test_a2_planning_schema.py `
  tests/integration/test_a2_planning_migration.py
poetry run mypy app/models/lab.py app/models/lab_planning.py --ignore-missing-imports
```

Expected: both commands exit 0.

## Task 4: Add immutable target, acceptance, and formula-lineage commands

**Files:**

- Create: `backend/app/repositories/lab_planning.py`
- Create: `backend/app/services/lab_planning.py`
- Create: `backend/tests/a2_planning_fixtures.py`
- Create: `backend/tests/unit/test_a2_planning_service.py`
- Modify: `backend/app/repositories/lab.py`
- Modify: `backend/app/services/lab_service.py`

- [ ] **Step 1: Write target lifecycle RED tests**

Place `_target_command`, `_formula_versions`, `_planning_graph`,
`_build_plan_command`, `_plan_at_status`, and `_approved_plan` in
`backend/tests/a2_planning_fixtures.py`; later A2.1 tests import them from that
module. Add asynchronous tests with these contracts:

```python
def _target_command(
    *, evidence_id: str, rationale: str
) -> TargetHypothesisInput:
    return TargetHypothesisInput(
        product_key="reference:iris-control",
        schema_version="a2-target-v1",
        author="Sol",
        provenance_activity={"activity": "test-fixture"},
        uncertainty_summary={"basis": "bounded-test"},
        rationale=rationale,
        lines=(
            TargetLineInput(
                line_id="target-line-jasmine",
                target_identity="Jasmine Absolute",
                source_name="Jasmine absolute reference",
                grade="absolute",
                presence_probability=0.95,
                target_raw_quantity=1.0,
                target_active_quantity=0.1,
                unit="g",
                concentration_fraction=0.1,
                concentration_basis="mass_fraction",
                functional_roles=("heart", "diffusion"),
                evidence_links=(evidence_id,),
                uncertainty={"standard_uncertainty_g": 0.01},
            ),
        ),
    )


async def _formula_versions(service: LabService):
    formula = await service.create_formula("A2 lineage fixture")
    parent = await service.add_formula_version(
        formula.id,
        brief={"name": "parent"},
        constraints={},
        components=(),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={"name": "child"},
        constraints={},
        components=(),
    )
    return parent, child


async def test_target_revision_is_append_only_and_hash_chained(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="target:jasmine",
        classification="EXACT",
        source_locator="test://target-jasmine",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    first = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Initial documentary hypothesis",
        )
    )
    second = await service.revise_target_hypothesis(
        first.id,
        _target_command(
            evidence_id=evidence.id,
            rationale="New documentary evidence",
        ),
    )
    assert second.target_id == first.target_id
    assert second.version_number == 2
    assert second.parent_version_id == first.id
    assert second.parent_sha256 == first.content_sha256
    assert await service.repository.get_target_version(first.id) == first


async def test_acceptance_references_one_immutable_target_version(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="target:acceptance",
        classification="EXACT",
        source_locator="test://target-acceptance",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    target = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Acceptance fixture",
        )
    )
    accepted = await service.accept_target(
        target.id, reviewer="Sol", rationale="Evidence gate passed"
    )
    assert accepted.target_hypothesis_version_id == target.id
    with pytest.raises(PlanningConflictError) as duplicate:
        await service.accept_target(
            target.id, reviewer="Sol", rationale="Duplicate"
        )
    assert duplicate.value.code == "TARGET_ALREADY_ACCEPTED"


async def test_formula_lineage_rejects_self_edge_and_cycle(db_session):
    service = LabService(db_session)
    parent, child = await _formula_versions(service)
    await service.link_formula_version(
        child.id,
        parent.id,
        relationship_kind="DERIVED_FROM",
        change={"kind": "REBALANCE"},
        rationale="Immutable revision",
    )
    with pytest.raises(PlanningConflictError) as cycle:
        await service.link_formula_version(
            parent.id,
            child.id,
            relationship_kind="DERIVED_FROM",
            change={"kind": "REBALANCE"},
            rationale="Cycle",
        )
    assert cycle.value.code == "FORMULA_VERSION_CYCLE"
```

Use complete `TargetHypothesisInput` and `TargetLineInput` fixtures containing
identity, active/raw quantity, unit, concentration basis, uncertainty,
functional roles, and evidence links.

- [ ] **Step 2: Run target tests to observe RED**

Run:

```powershell
poetry run pytest tests/unit/test_a2_planning_service.py -q --color=no
```

Expected: import or attribute failures for the missing planning service.

- [ ] **Step 3: Implement repository queries without transactions**

`LabPlanningRepositoryMixin` must provide:

```python
get_evidence_record(evidence_id)
get_target_version(version_id)
latest_target_version(target_id)
target_lines(version_id)
get_acceptance(acceptance_id)
acceptance_for_target_version(target_version_id)
formula_parent_edges(child_version_id)
formula_has_path(start_version_id, target_version_id)
get_mapping_version(version_id)
latest_mapping_version(mapping_id)
get_build_plan_version(version_id)
latest_build_plan_version(plan_id)
build_plan_lines(version_id)
reservation_events(reservation_id)
latest_reservation_event(reservation_id)
active_reserved_mass_g(stock_solution_id)
```

Every query is deterministic and explicitly ordered. The mixin uses
`self.session` and `self.add`; it never commits, rolls back, or begins a
transaction.

Compose it as:

```python
class LabRepository(LabPlanningRepositoryMixin):
    """Canonical repository with existing and A2 planning queries."""
```

- [ ] **Step 4: Implement immutable DTOs and stable domain errors**

The service module must define frozen DTOs:

```python
@dataclass(frozen=True, slots=True)
class TargetLineInput:
    line_id: str
    target_identity: str
    source_name: str
    grade: str
    presence_probability: float
    target_raw_quantity: float
    target_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    functional_roles: tuple[str, ...]
    evidence_links: tuple[str, ...]
    uncertainty: dict


@dataclass(frozen=True, slots=True)
class TargetHypothesisInput:
    product_key: str
    schema_version: str
    author: str
    provenance_activity: dict
    uncertainty_summary: dict
    rationale: str
    lines: tuple[TargetLineInput, ...]


@dataclass(frozen=True, slots=True)
class InventoryMappingInput:
    target_line_id: str
    stock_solution_id: str | None
    target_identity: str
    build_identity: str
    identity_status: str
    inventory_status: str
    substitution_class: str
    preserved_functions: tuple[str, ...]
    lost_functions: tuple[str, ...]
    confidence: float
    rationale: str
    evidence_links: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BuildPlanLineInput:
    line_id: str
    target_line_id: str
    target_identity: str
    inventory_mapping_version_id: str
    stock_solution_id: str
    planned_raw_quantity: float
    planned_active_quantity: float
    unit: str
    concentration_fraction: float
    concentration_basis: str
    density_g_ml: float | None
    density_source: str | None
    standard_uncertainty: float | None
    measurement_method: str
    resolution: float
    expected_transfer_loss: float
    substitution_class: str
    preserved_functions: tuple[str, ...]
    lost_functions: tuple[str, ...]
    rationale: str
    evidence_links: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BuildPlanInput:
    target_hypothesis_version_id: str
    accepted_target_version_id: str
    schema_version: str
    author: str
    inventory_snapshot_ref: str
    uncertainty_summary: dict
    rationale: str
    lines: tuple[BuildPlanLineInput, ...]
```

Each `__post_init__` rejects blank IDs/bases, non-finite values, invalid
fractions, nonpositive resolution, negative quantities/loss, and mismatched
raw/active quantity inputs.

DTO `evidence_links` values are canonical `LabEvidenceRecord.id` values. The
service verifies each ID and writes the appropriate FK-backed target, mapping,
or build-plan evidence-link row. It never stores evidence authority only in a
JSON list.

Define:

```python
class PlanningDomainError(ValueError):
    code = "PLANNING_ERROR"


class PlanningConflictError(PlanningDomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
```

- [ ] **Step 5: Implement target/acceptance/lineage commands**

`LabPlanningServiceMixin` uses `self._transaction()` and `self.repository`.
Implement:

```python
record_evidence(
    *,
    claim_key,
    classification,
    source_locator,
    source_version,
    method,
    assumptions,
    limitations,
    payload_sha256,
)
create_target_hypothesis(command: TargetHypothesisInput)
revise_target_hypothesis(parent_version_id, command: TargetHypothesisInput)
accept_target(target_version_id, reviewer, rationale)
link_formula_version(child_version_id, parent_version_id, *,
                     relationship_kind, change, rationale)
```

Use `engine.calibration.hashing.stable_json_hash` over a schema-tagged payload
that excludes database-generated IDs and timestamps. A revision copies
`parent_sha256` from the parent and gets a new immutable ID. Acceptance fails
if the target version is missing, already accepted, or the reviewer/rationale
is blank. Formula lineage checks both self-edge and transitive cycles before
insert.

`record_evidence` is a bounded persistence command for the existing
`LabEvidenceRecord`; it validates shape and hashes but does not assign,
upgrade, or reinterpret scientific authority.

Compose the service as:

```python
class LabService(LabPlanningServiceMixin):
    """Canonical transaction owner with existing and planning commands."""
```

Do not change `_transaction`; it remains the single write owner and retains
SQLite `BEGIN IMMEDIATE`.

- [ ] **Step 6: Run target lifecycle tests to GREEN**

Run:

```powershell
poetry run pytest tests/unit/test_a2_planning_service.py -q --color=no
```

Expected: target, acceptance, and formula-lineage tests pass.

## Task 5: Add mapping and immutable build-plan lifecycle

**Files:**

- Modify: `backend/app/services/lab_planning.py`
- Modify: `backend/app/repositories/lab_planning.py`
- Modify: `backend/tests/unit/test_a2_planning_service.py`

- [ ] **Step 1: Add mapping and build-plan RED tests**

Add:

```python
async def _planning_graph(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="planning:jasmine",
        classification="EXACT",
        source_locator="test://planning-jasmine",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    material = await service.create_material("Jasmine Absolute")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.1,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        density_g_ml=1.0,
        supplier="Test supplier",
        lot_number="LOT-A2-1",
    )
    target = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Planning graph fixture",
        )
    )
    target_line = (await service.repository.target_lines(target.id))[0]
    acceptance = await service.accept_target(
        target.id,
        reviewer="Sol",
        rationale="Fixture evidence accepted",
    )
    mapping = await service.create_inventory_mapping(
        InventoryMappingInput(
            target_line_id=target_line.id,
            stock_solution_id=stock.id,
            target_identity="Jasmine Absolute",
            build_identity="Jasmine Absolute",
            identity_status="EXACT",
            inventory_status="EXACT_LOT_AVAILABLE",
            substitution_class="EXACT",
            preserved_functions=("heart", "diffusion"),
            lost_functions=(),
            confidence=1.0,
            rationale="Exact physical lot",
            evidence_links=(evidence.id,),
        )
    )
    return service, target, acceptance, mapping, target_line, stock, evidence


def _build_plan_command(
    target,
    acceptance,
    mapping,
    target_line,
    stock,
    evidence,
) -> BuildPlanInput:
    return BuildPlanInput(
        target_hypothesis_version_id=target.id,
        accepted_target_version_id=acceptance.id,
        schema_version="a2-build-plan-v1",
        author="Sol",
        inventory_snapshot_ref="inventory-sha256:test-fixture",
        uncertainty_summary={"basis": "bounded-test"},
        rationale="Executable planning fixture",
        lines=(
            BuildPlanLineInput(
                line_id="build-line-jasmine",
                target_line_id=target_line.id,
                target_identity="Jasmine Absolute",
                inventory_mapping_version_id=mapping.id,
                stock_solution_id=stock.id,
                planned_raw_quantity=1.0,
                planned_active_quantity=0.1,
                unit="g",
                concentration_fraction=0.1,
                concentration_basis="mass_fraction",
                density_g_ml=1.0,
                density_source="lot record",
                standard_uncertainty=0.01,
                measurement_method="gravimetric",
                resolution=0.001,
                expected_transfer_loss=0.01,
                substitution_class="EXACT",
                preserved_functions=("heart", "diffusion"),
                lost_functions=(),
                rationale="Exact physical lot",
                evidence_links=(evidence.id,),
            ),
        ),
    )


async def _plan_at_status(db_session, requested_status: str):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    plan = await service.create_build_plan(
        _build_plan_command(
            target, acceptance, mapping, target_line, stock, evidence
        )
    )
    paths = {
        "DRAFT": (),
        "UNDER_REVIEW": ("UNDER_REVIEW",),
        "APPROVED": ("UNDER_REVIEW", "APPROVED"),
        "RESERVED": ("UNDER_REVIEW", "APPROVED", "RESERVED"),
        "EXECUTING": (
            "UNDER_REVIEW", "APPROVED", "RESERVED", "EXECUTING"
        ),
        "CLOSED": (
            "UNDER_REVIEW", "APPROVED", "RESERVED", "EXECUTING", "CLOSED"
        ),
    }
    for next_status in paths[requested_status]:
        plan = await service.transition_build_plan(
            plan.id,
            next_status=next_status,
            actor="Sol",
            rationale=f"Fixture transition to {next_status}",
        )
    return plan


async def test_mapping_never_rewrites_target_identity(db_session):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    assert mapping.target_line_id == target_line.id
    assert mapping.stock_solution_id == stock.id
    assert target_line.target_identity == "Jasmine Absolute"
    assert target.id == acceptance.target_hypothesis_version_id
    assert service is not None


async def test_build_plan_is_independent_and_revision_creates_new_rows(db_session):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    draft = await service.create_build_plan(
        _build_plan_command(
            target, acceptance, mapping, target_line, stock, evidence
        )
    )
    review = await service.transition_build_plan(
        draft.id,
        next_status="UNDER_REVIEW",
        actor="reviewer",
        rationale="Ready for review",
    )
    assert review.plan_id == draft.plan_id
    assert review.version_number == 2
    assert review.parent_version_id == draft.id
    assert review.parent_sha256 == draft.content_sha256
    assert await service.repository.build_plan_lines(draft.id)
    assert await service.repository.build_plan_lines(review.id)


@pytest.mark.parametrize(
    ("current", "next_status"),
    [
        ("DRAFT", "APPROVED"),
        ("UNDER_REVIEW", "RESERVED"),
        ("APPROVED", "CLOSED"),
    ],
)
async def test_build_plan_rejects_invalid_transition(
    db_session, current, next_status
):
    plan = await _plan_at_status(db_session, current)
    with pytest.raises(PlanningConflictError) as error:
        await LabService(db_session).transition_build_plan(
            plan.id,
            next_status=next_status,
            actor="Sol",
            rationale="Invalid transition",
        )
    assert error.value.code == "INVALID_BUILD_PLAN_TRANSITION"
```

- [ ] **Step 2: Run the new tests to observe RED**

Run the four mapping/build-plan test groups by node ID.

Expected: missing command failures.

- [ ] **Step 3: Implement versioned mapping**

`create_inventory_mapping` and `revise_inventory_mapping` must:

- require an existing target line;
- require an existing stock lot unless `inventory_status` is explicitly
  `EXACT_IDENTITY_NOT_IN_STOCK` or `NO_SUITABLE_STOCK`;
- preserve the target line and target version unchanged;
- store preserved/lost functions and evidence links;
- hash-chain revisions;
- reject a selected stock whose material identity contradicts an exact
  mapping.

- [ ] **Step 4: Implement build-plan creation and transitions**

`create_build_plan` must require:

- an existing immutable target version;
- its accepted-target record;
- at least one line;
- one unique target line and position per plan;
- selected physical stock for every executable line;
- explicit raw/active quantities, unit, fraction/basis, measurement method,
  resolution, transfer loss, rationale, and evidence links;
- a caller-supplied inventory snapshot reference.

`transition_build_plan` validates `BUILD_PLAN_TRANSITIONS`, copies the complete
line set to a new version, records actor/reviewer/rationale, and creates a new
content hash chained to the parent. It never updates the previous row.

- [ ] **Step 5: Run mapping/build-plan tests to GREEN**

Run:

```powershell
poetry run pytest tests/unit/test_a2_planning_service.py -q --color=no
```

Expected: all tests pass.

## Task 6: Add atomic reservation events and concurrency protection

**Files:**

- Modify: `backend/app/services/lab_planning.py`
- Modify: `backend/app/repositories/lab_planning.py`
- Create: `backend/tests/integration/test_a2_planning_transactions.py`

- [ ] **Step 1: Write reservation RED tests**

Add:

```python
from dataclasses import replace


async def _approved_plan(db_session):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    draft = await service.create_build_plan(
        _build_plan_command(
            target, acceptance, mapping, target_line, stock, evidence
        )
    )
    review = await service.transition_build_plan(
        draft.id,
        next_status="UNDER_REVIEW",
        actor="reviewer",
        rationale="Review requested",
    )
    approved = await service.transition_build_plan(
        review.id,
        next_status="APPROVED",
        actor="reviewer",
        rationale="Plan approved",
    )
    line = (await service.repository.build_plan_lines(approved.id))[0]
    return service, approved, line, stock


async def test_reservation_is_atomic_idempotent_and_reduces_available_stock(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    event = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-1",
        actor="Sol",
        rationale="Approved build",
    )
    retry = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-1",
        actor="Sol",
        rationale="Approved build",
    )
    assert retry.id == event.id
    assert await service.available_stock_g(stock.id) == pytest.approx(
        stock.initial_mass_g - 1.25
    )


async def test_reservation_idempotency_conflict_rolls_back(db_session):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    event = await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="reserve-plan-line-conflict",
        actor="Sol",
        rationale="Approved build",
    )
    with pytest.raises(PlanningConflictError) as error:
        await service.reserve_inventory(
            build_plan_version_id=approved_plan.id,
            build_plan_line_id=line.id,
            stock_solution_id=stock.id,
            reserved_mass_g=1.5,
            idempotency_key="reserve-plan-line-conflict",
            actor="Sol",
            rationale="Different command bytes",
        )
    assert error.value.code == "RESERVATION_IDEMPOTENCY_CONFLICT"
    assert len(
        await service.repository.reservation_events(event.reservation_id)
    ) == 1


async def test_concurrent_reservations_cannot_overreserve_shared_stock(
    test_engine,
):
    factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as setup_session:
        service, target, acceptance, mapping, target_line, stock, evidence = (
            await _planning_graph(setup_session)
        )
        base_command = _build_plan_command(
            target, acceptance, mapping, target_line, stock, evidence
        )

        async def approve(command: BuildPlanInput):
            draft = await service.create_build_plan(command)
            review = await service.transition_build_plan(
                draft.id,
                next_status="UNDER_REVIEW",
                actor="reviewer",
                rationale="Concurrent fixture review",
            )
            approved = await service.transition_build_plan(
                review.id,
                next_status="APPROVED",
                actor="reviewer",
                rationale="Concurrent fixture approval",
            )
            line = (
                await service.repository.build_plan_lines(approved.id)
            )[0]
            return approved, line

        left_plan, left_line = await approve(base_command)
        right_plan, right_line = await approve(
            replace(
                base_command,
                rationale="Second executable plan sharing one stock lot",
            )
        )

    async def reserve(plan, line, idempotency_key: str):
        async with factory() as session:
            return await LabService(session).reserve_inventory(
                build_plan_version_id=plan.id,
                build_plan_line_id=line.id,
                stock_solution_id=stock.id,
                reserved_mass_g=7.5,
                idempotency_key=idempotency_key,
                actor="Sol",
                rationale="Concurrent reservation test",
            )

    results = await asyncio.gather(
        reserve(left_plan, left_line, "reservation-a"),
        reserve(right_plan, right_line, "reservation-b"),
        return_exceptions=True,
    )
    assert sum(isinstance(result, LabInventoryReservationEvent)
               for result in results) == 1
    assert sum(
        isinstance(result, InsufficientAvailableStockError)
        for result in results
    ) == 1
    async with factory() as check_session:
        assert await LabService(check_session).available_stock_g(
            stock.id
        ) == pytest.approx(2.5)
```

Also test terminal reservation transitions, duplicate sequence rejection,
rollback on unknown plan/line/stock, and the requirement that the reservation
stock matches the build line.

- [ ] **Step 2: Run reservation tests to observe RED**

Run:

```powershell
poetry run pytest `
  tests/integration/test_a2_planning_transactions.py `
  -q --color=no
```

Expected: missing reservation-command failures.

- [ ] **Step 3: Implement reservation availability and commands**

Available stock is:

```text
canonical stock balance
- latest nonterminal RESERVED mass for that stock
```

Implement:

```python
available_stock_g(stock_solution_id)
reserve_inventory(
    *,
    build_plan_version_id,
    build_plan_line_id,
    stock_solution_id,
    reserved_mass_g,
    idempotency_key,
    actor,
    rationale,
)
transition_reservation(reservation_id, next_state, *,
                       idempotency_key, actor, rationale)
```

All commands execute inside the existing serialized service transaction.
Idempotent replay returns the existing event only when the complete normalized
command payload matches. Reusing a key with different bytes raises
`RESERVATION_IDEMPOTENCY_CONFLICT`. Over-reservation raises
`INSUFFICIENT_AVAILABLE_STOCK` and leaves no partial rows.

When all executable lines are reserved, create a new build-plan version with
status `RESERVED`; do not mutate the approved plan. No inventory movement is
created until a later confirmed bottle action.

- [ ] **Step 4: Run transaction tests to GREEN**

Run:

```powershell
poetry run pytest `
  tests/integration/test_a2_planning_transactions.py `
  tests/integration/test_lab_transactions.py `
  -q --color=no
```

Expected: all existing and new transaction tests pass.

## Task 7: Extend deterministic export/import and backup compatibility

**Files:**

- Modify: `backend/app/services/lab_export.py`
- Create: `backend/tests/integration/test_a2_planning_export.py`
- Modify: `backend/tests/integration/test_backup_restore.py`

- [ ] **Step 1: Write export/import RED tests**

Add tests that prove:

```python
V1_TABLE_ORDER = (
    "lab_evidence_records",
    "lab_materials",
    "lab_material_aliases",
    "lab_material_properties",
    "lab_restrictions",
    "lab_constituents",
    "lab_stock_solutions",
    "lab_formulas",
    "lab_formula_versions",
    "lab_formula_components",
    "lab_batches",
    "lab_bottles",
    "lab_bottle_events",
    "lab_bottle_event_effects",
    "lab_inventory_movements",
    "lab_bottle_measurements",
    "lab_experiments",
    "lab_samples",
    "lab_applications",
    "lab_observations",
    "lab_pairwise_comparisons",
    "lab_predictions",
    "lab_outcomes",
)


async def _planning_row_count(session) -> int:
    total = 0
    for table_name in sorted(PLANNING_TABLES):
        table = Base.metadata.tables[table_name]
        total += int(
            await session.scalar(select(func.count()).select_from(table)) or 0
        )
    return total


async def test_v2_export_orders_complete_planning_graph(db_session):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="export-reservation",
        actor="Sol",
        rationale="Complete export graph",
    )
    packet = await LabExportService(db_session).export_workspace()
    assert packet["format_revision"] == "lab-export-v2"
    assert set(PLANNING_TABLES) <= set(packet["tables"])
    assert packet["ordering_contract"]["target_versions"] == [
        "target_id", "version_number", "id"
    ]
    assert packet["ordering_contract"]["build_plan_versions"] == [
        "plan_id", "version_number", "id"
    ]
    assert packet["ordering_contract"]["reservation_events"] == [
        "reservation_id", "sequence", "id"
    ]


async def test_v2_export_import_is_byte_deterministic_and_idempotent(
    db_session,
):
    service, approved_plan, line, stock = await _approved_plan(db_session)
    await service.reserve_inventory(
        build_plan_version_id=approved_plan.id,
        build_plan_line_id=line.id,
        stock_solution_id=stock.id,
        reserved_mass_g=1.25,
        idempotency_key="roundtrip-reservation",
        actor="Sol",
        rationale="Round-trip export graph",
    )
    exporter = LabExportService(db_session)
    packet = await exporter.export_workspace()
    before = await exporter.canonical_bytes()
    result = await exporter.import_workspace(packet)
    after = await exporter.canonical_bytes()
    assert result.inserted == 0
    assert result.skipped == sum(
        len(rows) for rows in packet["tables"].values()
    )
    assert after == before


async def test_v1_packet_imports_without_inventing_planning_authority(
    db_session,
):
    packet = {
        "format_revision": "lab-export-v1",
        "tables": {name: [] for name in V1_TABLE_ORDER},
    }
    result = await LabExportService(db_session).import_workspace(packet)
    assert result.inserted == 0
    assert result.skipped == 0
    assert await _planning_row_count(db_session) == 0
```

- [ ] **Step 2: Run export tests to observe RED**

Expected: format-revision and missing-table failures.

- [ ] **Step 3: Implement v2 export with v1 reader compatibility**

Set the writer revision to `lab-export-v2`. Accept `lab-export-v1` and
`lab-export-v2` on import. Extend `_TABLE_ORDER` in strict FK order. A v1
packet omits planning tables and imports zero planning rows; it must never
infer target acceptance or build authority.

Add deterministic ordering for target versions/lines, mapping versions, build
plans/lines, and reservation events. Extend unit and provenance contracts with
planning quantities, target evidence, content hashes, and inventory snapshots.

- [ ] **Step 4: Bind backup tests to the new head**

Update the expected Alembic head to `20260730_0001`. Verify a file-backed
released-schema copy is snapshotted before upgrade, upgraded, backed up,
validated, staged, and restored without losing representative legacy or
planning rows.

- [ ] **Step 5: Run export/backup tests to GREEN**

Run:

```powershell
poetry run pytest `
  tests/integration/test_a2_planning_export.py `
  tests/integration/test_backup_restore.py `
  -q --color=no
```

Expected: all selected tests pass.

## Task 8: Expose thin versioned planning operations

**Files:**

- Create: `backend/app/schemas/lab_planning.py`
- Create: `backend/app/api/v1/endpoints/lab_planning.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/integration/test_a2_planning_api.py`

- [ ] **Step 1: Write API RED tests**

Cover:

- `POST /api/v1/lab/v2/targets`
- `POST /api/v1/lab/v2/targets/{version_id}/accept`
- `POST /api/v1/lab/v2/formula-versions/{child_id}/parents`
- `POST /api/v1/lab/v2/inventory-mappings`
- `POST /api/v1/lab/v2/build-plans`
- `POST /api/v1/lab/v2/build-plans/{version_id}/transitions`
- `POST /api/v1/lab/v2/reservations`
- `POST /api/v1/lab/v2/reservations/{reservation_id}/transitions`
- `GET /api/v1/lab/v2/targets/{version_id}`
- `GET /api/v1/lab/v2/build-plans/{version_id}`

Require that:

```python
assert response.json() == {
    "error": {
        "code": "INVALID_BUILD_PLAN_TRANSITION",
        "message": "Build plan cannot transition from DRAFT to APPROVED.",
    }
}
```

for a representative conflict. Also require 404 stable codes for unknown
target, acceptance, formula version, mapping, plan, line, stock, and
reservation identities.

- [ ] **Step 2: Run API tests to observe RED**

Run:

```powershell
poetry run pytest tests/integration/test_a2_planning_api.py -q --color=no
```

Expected: all routes return 404 before router creation.

- [ ] **Step 3: Implement strict Pydantic contracts**

Set every request model to:

```python
model_config = ConfigDict(extra="forbid")
```

Use finite numeric constraints, fractions bounded to `[0,1]`, nonnegative
quantities/loss, positive resolution, nonblank identifiers, timezone-aware
review timestamps, and explicit quantity units and concentration bases.

Responses return immutable IDs, stable IDs, version/sequence, status, hashes,
parent references, and `created_at`. Do not expose ORM internals or accept
caller-supplied database IDs.

- [ ] **Step 4: Implement thin routes and stable errors**

Each route:

1. validates a Pydantic request;
2. constructs one service DTO;
3. calls one `LabService` command;
4. serializes the returned canonical record;
5. maps `PlanningDomainError.code` to a stable JSON envelope.

No route calls `session.add`, `commit`, `rollback`, or engine persistence.
Mount the new router in `backend/app/api/v1/router.py` under `/lab/v2`.
Do not modify the existing user-edited lab endpoint or schema files.

- [ ] **Step 5: Run API and existing compatibility tests to GREEN**

Run:

```powershell
poetry run pytest `
  tests/integration/test_a2_planning_api.py `
  tests/integration/test_lab_api.py `
  tests/integration/test_api_endpoints.py `
  -q --color=no
```

Expected: all selected tests pass. Existing endpoint shapes remain unchanged.

## Task 9: Verify the A2.1 slice and create a bounded checkpoint

**Files:**

- Create: `docs/verification/a2_slice1/README.md`
- Read: `verification_runs/project_verification.json`
- Read: `data/perfumery_kb.db`
- Read: `perfume_chem.db`

- [ ] **Step 1: Run focused A2.1 tests**

Run:

```powershell
poetry run pytest `
  tests/unit/test_a2_planning_schema.py `
  tests/unit/test_a2_planning_service.py `
  tests/integration/test_a2_planning_migration.py `
  tests/integration/test_a2_planning_transactions.py `
  tests/integration/test_a2_planning_export.py `
  tests/integration/test_a2_planning_api.py `
  -q --color=no
```

Expected: all pass with zero failures, errors, or skips.

- [ ] **Step 2: Run complete backend static and test gates**

Run from `backend`:

```powershell
poetry run ruff check app alembic tests
poetry run mypy app --ignore-missing-imports
poetry run pytest -q --color=no `
  --basetemp=../output/verification-temp/a2-slice1-backend `
  --junitxml=../verification_runs/a2-slice1-backend.xml
```

Expected: all commands exit 0.

- [ ] **Step 3: Run the root suite and canonical verifier**

Using the supported Python 3.11 environment, run:

```powershell
python -m pytest -q --color=no `
  --basetemp=output/verification-temp/a2-slice1-root `
  --junitxml=verification_runs/a2-slice1-root.xml
python scripts/pipeline_audit.py project-verify --json
```

Expected:

- all root tests pass;
- all backend tests pass;
- Ruff and MyPy pass;
- package build, wheel smoke, migration, backup/restore, and golden locks pass;
- formula artifacts contain no blocking `STALE` or `TAMPERED`;
- only declared optional Docker checks may be skipped;
- scientific release remains blocked unless independent held-out sensory
  evidence has actually changed.

- [ ] **Step 4: Restore any verifier knowledge-database side effect**

Compare `data/perfumery_kb.db` with the protected pre-plan archive. If the
canonical verifier changed it, copy the archived bytes to a separate restore
candidate, verify its SHA-256 and SQLite integrity, then restore the
authoritative path and prove both hashes match:

```text
5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1
```

Do not display or extract any sensitive archive.

- [ ] **Step 5: Prove the canonical database was not migrated**

`perfume_chem.db` must remain zero bytes with SHA-256:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

All migration evidence in this slice comes from empty and representative test
copies. Applying the migration to the canonical database is deferred until the
later A2 migration-acceptance slice passes backup/restore/export/import gates.

- [ ] **Step 6: Record evidence without promotion**

In `docs/verification/a2_slice1/README.md`, record:

- starting and ending commit SHA;
- recovery package path and verification result;
- changed paths;
- RED and GREEN test commands/counts;
- single Alembic head and migration-copy results;
- backend/root/canonical verifier counts;
- artifact classifications;
- canonical and knowledge database hashes;
- Docker skips;
- DeepLuna job IDs and any rejected worker claims;
- `A2_SLICE1_PASS` or the exact blocker;
- `A2_COMPLETE=false`, `A3_STARTED=false`, and
  `SCIENTIFIC_RELEASE_BLOCKED=true` unless executable evidence proves
  otherwise.

- [ ] **Step 7: Commit only after every slice gate is GREEN**

Stage only the files named in this plan. Verify the staged list contains no
environment file, credential, database, generated wheel, archive, unrelated
dirty path, or A2 Slice 2 work.

Commit:

```powershell
git commit -m "build(a2): add canonical planning persistence"
```

Expected: one bounded A2.1 implementation checkpoint.

- [ ] **Step 8: Stop at the slice boundary**

Report the checkpoint, tests, migration-copy evidence, database hashes,
optional skips, remaining A2 work, and scientific-release blocker. Do not
begin analytical/regulatory persistence, legacy adapters, canonical database
migration, A2 Slice 2, or A3 until the user accepts this checkpoint.

## A2.1 exit gate

The slice passes only when all of the following are true:

- the eleven canonical planning tables exist in ORM metadata and the explicit
  migration;
- migration upgrade from empty and `20260717_0001` copies passes;
- downgrade to `20260717_0001` passes;
- one Alembic head exists;
- append-only, FK, uniqueness, status, quantity, sequence, and idempotency
  constraints are exercised at the database boundary;
- target and build remain independent;
- target acceptance and formula lineage are immutable;
- build-plan revisions hash-chain and copy complete line content;
- concurrent reservations cannot make available stock negative;
- new versioned APIs are thin and return stable error codes;
- old API compatibility tests remain green;
- v1 export packets import without inventing planning authority;
- v2 export/import is deterministic and idempotent;
- backend, root, artifact, package, wheel, and canonical verifier gates pass;
- existing dirty work and database bytes remain protected;
- a bounded checkpoint SHA exists.

Passing this gate establishes only `A2_SLICE1_PASS`. It does not establish the
full A2 exit gate, scientific release readiness, or permission to begin A3.
