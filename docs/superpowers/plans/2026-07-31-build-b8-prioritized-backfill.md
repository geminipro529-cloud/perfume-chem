# Build B8 Prioritized Scientific-Data Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Codex
> subagents are prohibited for this project. DeepLuna Fast may perform only
> bounded read-only audits after a fresh exact-project readiness check.

**Goal:** Add a reproducible, append-only B8 campaign that ranks scientific
backfill work by decision value, resolves accepted gaps only through exact B7
authority, and emits stratified dashboards without one aggregate coverage
score.

**Architecture:** Five new append-only tables freeze campaigns, material
priorities, typed priority signals, normalized evidence gaps, and dashboard
cells. A code-owned policy derives a strict lexicographic rank from exact
upstream records; accepted gaps must reconstruct through B7. A separate
read-only script projects the current inventory against the frozen B0
scientific-truth inventory without promoting legacy values.

**Tech Stack:** Python 3.11, SQLAlchemy 2 async ORM, Alembic, SQLite,
Pydantic-compatible command dataclasses, pytest/pytest-asyncio, Ruff, mypy.

---

## File map

- Create `backend/app/models/lab_backfill.py`: B8 enums and five ORM tables.
- Modify `backend/app/models/lab.py`: import/register B8 models.
- Create `backend/app/repositories/lab_backfill.py`: persistence-only B8
  lookups and ordered child queries.
- Modify `backend/app/repositories/lab.py`: compose the B8 repository mixin.
- Create `backend/app/services/lab_backfill.py`: policy, commands, typed
  resolution, ranking, dashboard generation, persistence, reconstruction.
- Modify `backend/app/services/lab_service.py`: compose the B8 service mixin.
- Create
  `backend/alembic/versions/20260731_0012_b8_prioritized_backfill.py`:
  additive schema and append-only triggers.
- Create `backend/tests/unit/test_b8_backfill_schema.py`: model-policy parity
  and constraint declarations.
- Create `backend/tests/unit/test_b8_backfill_service.py`: pure policy,
  ranking, gap, and dashboard tests.
- Create `backend/tests/integration/test_b8_backfill_migration.py`: operational
  migration/constraint/trigger round trip.
- Create `backend/tests/integration/test_b8_backfill_e2e.py`: canonical
  B1-B8 creation/reconstruction and negative paths.
- Modify `backend/tests/integration/test_lab_migration.py`: advance expected
  head to `20260731_0012`.
- Modify `backend/tests/integration/test_backup_restore.py`: advance expected
  head to `20260731_0012`.
- Create `scripts/b8_backfill_dashboard.py`: read-only B0/current-inventory
  projection.
- Create `tests/test_b8_backfill_dashboard.py`: projection determinism and
  fail-closed status tests.
- Create `docs/verification/b8/`: captured gate evidence after implementation.

### Task 1: Freeze the B8 policy and schema contract with RED tests

**Files:**

- Create: `backend/tests/unit/test_b8_backfill_schema.py`
- Create: `backend/tests/unit/test_b8_backfill_service.py`

- [ ] **Step 1: Write schema-policy tests**

Assert exact closed vocabularies:

```python
assert BACKFILL_SIGNAL_TYPES == (
    "CURRENT_INVENTORY",
    "ACTIVE_FORMULA",
    "SHIPPED_FORMULA",
    "REFERENCE_FORMULA",
    "HIGH_DOSE_STRUCTURE",
    "POTENT_TRACE",
    "REGULATORY_DRIVER",
    "FAMILY_DRIVER",
    "ANALYTICAL_STANDARD",
    "NATURAL_CONSTITUENT",
    "MODEL_SENSITIVITY",
)
assert BACKFILL_REQUIREMENT_TYPES == (
    "EXACT_IDENTITY",
    "GRADE_IDENTITY",
    "MOLECULAR_WEIGHT",
    "DENSITY",
    "VAPOR_PRESSURE",
    "CONTEXTUAL_THRESHOLD",
    "SAFETY_DOCUMENTATION",
    "RETENTION_INDEX",
    "ANALYTICAL_REFERENCE",
    "NATURAL_LOT_COMPOSITION",
)
assert BACKFILL_GAP_STATES == (
    "MISSING",
    "UNKNOWN",
    "WEAK",
    "CONFLICTED",
    "ACCEPTED_SCOPED",
    "ACCEPTED_EXACT",
    "NOT_APPLICABLE",
)
```

Assert five exact table names, all required columns, unique/check/FK/index
names, false-only release authority, one-of typed signal shape, accepted-gap
B7-link shape, nonnegative counts, and dashboard state-count reconciliation.

- [ ] **Step 2: Write pure ranking tests**

Build frozen `ResolvedBackfillMaterial` fixtures and assert:

```python
ordered = rank_backfill_materials(fixtures)
assert [row.material_id for row in ordered] == [
    "owned",
    "active",
    "high-dose",
    "potent-trace",
    "regulatory",
    "standard",
    "natural",
    "sensitive",
    "unknown",
]
```

Add permutations proving input order does not change rank; large model
sensitivity cannot outrank inventory; unknown dimensions sort behind known
values only in their own position; and ties resolve by critical gaps, total
gaps, canonical name, then material ID.

- [ ] **Step 3: Write pure dashboard tests**

Assert all seven required dimensions are emitted, state counts reconcile to
their explicit denominator, evidence classes remain separate, and these keys
raise `ValueError`:

```python
("OVERALL", "TOTAL_CONFIDENCE", "COVERAGE_SCORE", "CONFIDENCE_PERCENT")
```

- [ ] **Step 4: Run tests and verify RED**

Run from `backend`:

```powershell
python -m pytest tests/unit/test_b8_backfill_schema.py tests/unit/test_b8_backfill_service.py --color=no -q --basetemp=../output/pytest-temp-backend/b8-red-schema
```

Expected: collection fails because `app.models.lab_backfill` and
`app.services.lab_backfill` do not exist.

- [ ] **Step 5: Commit RED tests**

```powershell
git add backend/tests/unit/test_b8_backfill_schema.py backend/tests/unit/test_b8_backfill_service.py
git commit -m "test: define Build B8 backfill authority contract"
```

### Task 2: Add the five-table append-only schema

**Files:**

- Create: `backend/app/models/lab_backfill.py`
- Modify: `backend/app/models/lab.py`
- Create:
  `backend/alembic/versions/20260731_0012_b8_prioritized_backfill.py`
- Create: `backend/tests/integration/test_b8_backfill_migration.py`

- [ ] **Step 1: Define model constants and tables**

Use these exact classes:

```python
class LabBackfillCampaignVersion(LabRecord): ...
class LabBackfillMaterialPriority(LabRecord): ...
class LabBackfillPrioritySignalLink(LabRecord): ...
class LabBackfillGapItem(LabRecord): ...
class LabBackfillDashboardCell(LabRecord): ...
```

Export:

```python
BACKFILL_TABLE_NAMES = {
    "lab_backfill_campaign_versions",
    "lab_backfill_material_priorities",
    "lab_backfill_priority_signal_links",
    "lab_backfill_gap_items",
    "lab_backfill_dashboard_cells",
}
```

Every JSON field uses a non-null default where absence is meaningful. Hashes
are 64 lowercase hexadecimal characters at service boundaries and length 64
at database boundaries.

- [ ] **Step 2: Register models**

Import the five classes and `BACKFILL_TABLE_NAMES` at the bottom of
`backend/app/models/lab.py`, following B7's late-import pattern so
`LabRecord` exists before the module imports.

- [ ] **Step 3: Write the migration**

Create revision `20260731_0012`, down revision `20260731_0011`. Use explicit
Alembic types and names; do not import application models, use
`bulk_insert`, or use `checkfirst`. Create all indexes/constraints and
`BEFORE UPDATE`/`BEFORE DELETE` SQLite triggers for each table. Downgrade
drops triggers, indexes as required, then tables in child-first order.

- [ ] **Step 4: Add migration RED/GREEN coverage**

Cover:

- `0011 -> 0012` upgrade with zero B8 rows;
- all five tables and current head;
- downgrade to `0011`, re-upgrade to `0012`;
- every FK/check/unique constraint;
- one-of signal source shape;
- accepted/nonaccepted gap-link shape;
- dashboard reconciliation;
- append-only update/delete rejection; and
- ORM/migration column parity.

- [ ] **Step 5: Run schema and migration tests**

```powershell
python -m pytest tests/unit/test_b8_backfill_schema.py tests/integration/test_b8_backfill_migration.py --color=no -q --basetemp=../output/pytest-temp-backend/b8-schema-green
```

Expected: pass.

- [ ] **Step 6: Commit schema**

```powershell
git add backend/app/models/lab.py backend/app/models/lab_backfill.py backend/alembic/versions/20260731_0012_b8_prioritized_backfill.py backend/tests/integration/test_b8_backfill_migration.py
git commit -m "feat: add Build B8 prioritized backfill schema"
```

### Task 3: Implement persistence and the pure priority engine

**Files:**

- Create: `backend/app/repositories/lab_backfill.py`
- Modify: `backend/app/repositories/lab.py`
- Create: `backend/app/services/lab_backfill.py`
- Modify: `backend/app/services/lab_service.py`

- [ ] **Step 1: Add repository methods**

Implement exact-ID getters plus ordered child reads:

```python
async def get_backfill_campaign_version(self, version_id: str): ...
async def latest_backfill_campaign_version(self, campaign_key: str): ...
async def backfill_material_priorities(self, campaign_version_id: str): ...
async def backfill_priority_signals(self, material_priority_id: str): ...
async def backfill_gap_items(self, material_priority_id: str): ...
async def backfill_dashboard_cells(self, campaign_version_id: str): ...
async def get_formula_component(self, component_id: str): ...
async def get_analytical_sequence_entry(self, entry_id: str): ...
async def get_regulatory_composition_entry(self, entry_id: str): ...
```

Repository methods perform no ranking, authority decisions, or transaction
ownership.

- [ ] **Step 2: Define frozen commands and policy**

Add frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class BackfillSignalCommand:
    signal_type: str
    source_id: str
    operational_status: str | None = None
    normalized_sensitivity: float | None = None

@dataclass(frozen=True, slots=True)
class BackfillGapCommand:
    requirement_type: str
    state: str
    evidence_class: str
    claim_authority_version_id: str | None
    applicability_scope: Mapping[str, object]
    conflicts: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class BackfillMaterialCommand:
    material_id: str
    chemical_family: str | None
    signals: tuple[BackfillSignalCommand, ...]
    gaps: tuple[BackfillGapCommand, ...]

@dataclass(frozen=True, slots=True)
class CreateBackfillCampaignCommand:
    campaign_key: str
    name: str
    purpose: str
    as_of_utc: datetime
    reviewer_pseudonym: str
    reviewed_at: datetime
    materials: tuple[BackfillMaterialCommand, ...]
    parent_version_id: str | None = None
```

Freeze `BACKFILL_PRIORITY_POLICY_V1` with the eight ordered dimensions and
hash its canonical JSON.

- [ ] **Step 3: Implement pure canonicalization/ranking/dashboard helpers**

Implement and unit-test:

```python
def canonical_json(value: object) -> str: ...
def content_sha256(value: object) -> str: ...
def rank_backfill_materials(
    materials: Sequence[ResolvedBackfillMaterial],
) -> tuple[RankedBackfillMaterial, ...]: ...
def build_backfill_dashboard(
    materials: Sequence[RankedBackfillMaterial],
) -> tuple[BackfillDashboardProjection, ...]: ...
```

Use `Decimal(str(value))` for rank-key numeric normalization. Reject NaN,
infinity, booleans-as-numbers, out-of-range sensitivity, duplicate signals,
duplicate requirements, absent required requirements, and banned dashboard
keys.

- [ ] **Step 4: Compose repository and service mixins**

Add `LabBackfillRepositoryMixin` to `LabRepository` and
`LabBackfillServiceMixin` to `LabService` without changing unrelated
ordering or behavior.

- [ ] **Step 5: Run unit tests**

```powershell
python -m pytest tests/unit/test_b8_backfill_schema.py tests/unit/test_b8_backfill_service.py --color=no -q --basetemp=../output/pytest-temp-backend/b8-pure-green
```

Expected: pure policy/rank/dashboard tests pass; integration creation tests do
not yet exist.

- [ ] **Step 6: Commit the pure engine**

```powershell
git add backend/app/repositories/lab.py backend/app/repositories/lab_backfill.py backend/app/services/lab_service.py backend/app/services/lab_backfill.py backend/tests/unit/test_b8_backfill_service.py
git commit -m "feat: rank Build B8 backfill campaigns"
```

### Task 4: Enforce typed upstream signals and B7-only gap resolution

**Files:**

- Modify: `backend/app/services/lab_backfill.py`
- Modify: `backend/app/repositories/lab_backfill.py`
- Create: `backend/tests/integration/test_b8_backfill_e2e.py`

- [ ] **Step 1: Write canonical fixture helpers**

Reuse public B1-B7 service commands to build accepted source, observation,
selection, OAV, rule, analytical, regulatory, and claim-authority rows. Do not
insert canonical authority rows directly except in tests explicitly proving a
database constraint.

- [ ] **Step 2: Write signal negative tests**

Prove rejection or unknown classification for:

- stock bound to another material or nonpositive balance;
- formula component bound to another material;
- active/shipped formula without reviewed `LOCAL_RECORD` declaration;
- incomplete formula totals for high-dose calculation;
- withheld or non-strict OAV;
- non-authoritative/rejected knowledge rule;
- failed/unknown regulatory snapshot;
- analytical sequence entry without exact
  `level_json["material_id"]`;
- natural composition entry with absent material or incomplete profile; and
- prediction without exact
  `prediction_json["normalized_sensitivity_by_material"][material_id]`.

- [ ] **Step 3: Write gap-resolution negative tests**

For every accepted state, prove rejection of:

- missing B7 link;
- `ADVISORY_ONLY`, `WITHHOLD_UNKNOWN`, or `BLOCK`;
- subject/material mismatch;
- claim-type/requirement mismatch;
- identity/condition scope mismatch;
- reconstructed upstream/content hash mismatch;
- scoped authority labeled exact; and
- nonaccepted state carrying a B7 link.

- [ ] **Step 4: Implement `create_backfill_campaign`**

Resolve and canonicalize all inputs before opening the persistence block.
Within one `async with self.session.begin()` transaction, add campaign,
priority, signal, gap, and dashboard rows. On any error, persist zero B8 rows.

- [ ] **Step 5: Implement `reconstruct_backfill_campaign`**

Reload ordered children, re-resolve every typed source, call
`reconstruct_claim_authority` for accepted gaps, recompute ranks/dashboard,
and compare every stored hash/count. Return an immutable projection only after
all checks pass.

- [ ] **Step 6: Run exact B8 service/e2e tests**

```powershell
python -m pytest tests/unit/test_b8_backfill_service.py tests/integration/test_b8_backfill_e2e.py --color=no -q --basetemp=../output/pytest-temp-backend/b8-e2e-green
```

Expected: pass.

- [ ] **Step 7: Commit authority enforcement**

```powershell
git add backend/app/repositories/lab_backfill.py backend/app/services/lab_backfill.py backend/tests/integration/test_b8_backfill_e2e.py
git commit -m "feat: enforce Build B8 backfill evidence lineage"
```

### Task 5: Add the current-workspace read-only dashboard projection

**Files:**

- Create: `scripts/b8_backfill_dashboard.py`
- Create: `tests/test_b8_backfill_dashboard.py`

- [ ] **Step 1: Write projection RED tests**

Use small temporary inventory/B0 fixtures. Assert alias-aware matching,
duplicate collapse, unavailable-stock separation, per-property/evidence counts,
all seven dimensions, explicit unknown active-formula/family/sensitivity
cells, deterministic JSON bytes, and absence of aggregate score/percentage
keys.

- [ ] **Step 2: Implement the projection**

Expose:

```python
def build_workspace_backfill_projection(
    *,
    inventory_path: Path,
    scientific_inventory_path: Path,
) -> dict[str, object]: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

The CLI writes only when an explicit `--output` path is supplied. It reads no
database, network, environment, or credential source. Legacy rows always
remain non-promoting; `LEGACY_UNREVIEWED` cannot become accepted.

- [ ] **Step 3: Run projection tests**

```powershell
python -m pytest tests/test_b8_backfill_dashboard.py --color=no -q --basetemp=output/pytest-temp/b8-dashboard
```

Expected: pass.

- [ ] **Step 4: Generate the bounded B8 verification projection**

```powershell
python -B scripts/b8_backfill_dashboard.py --inventory inventory.txt --scientific-inventory docs/verification/b0/scientific_truth_inventory.json.gz --output docs/verification/b8/current_inventory_gap_projection.json
```

Validate JSON and verify no secret-like values before staging.

- [ ] **Step 5: Commit projection code**

```powershell
git add scripts/b8_backfill_dashboard.py tests/test_b8_backfill_dashboard.py
git commit -m "feat: project Build B8 current inventory gaps"
```

Do not commit the generated projection until the final B8 gate package.

### Task 6: Advance compatibility head and run the complete B8 gate

**Files:**

- Modify: `backend/tests/integration/test_lab_migration.py`
- Modify: `backend/tests/integration/test_backup_restore.py`
- Create: `docs/verification/b8/prioritized_backfill_gate.md`
- Create: `docs/verification/b8/prioritized_backfill_gate.json`
- Create: `docs/verification/b8/logs/*`

- [ ] **Step 1: Advance migration constants**

Set canonical expected head to `20260731_0012`. First reproduce the expected
stale-head failures, then change only the two constants and rerun the focused
cases.

- [ ] **Step 2: Run exact B8 gate**

```powershell
python -m pytest tests/unit/test_b8_backfill_schema.py tests/unit/test_b8_backfill_service.py tests/integration/test_b8_backfill_migration.py tests/integration/test_b8_backfill_e2e.py --color=no -q --basetemp=../output/pytest-temp-backend/b8-exact-final
```

- [ ] **Step 3: Run A2 through B8 compatibility**

Run the complete A2 and B1-B8 schema/service/migration/e2e set plus
`test_lab_migration.py` and `test_backup_restore.py`, with no PTY, no ANSI,
captured stdout/stderr, and an explicit 15-minute timeout.

- [ ] **Step 4: Run static gates**

```powershell
python -m ruff check backend/app/models/lab.py backend/app/models/lab_backfill.py backend/app/repositories/lab.py backend/app/repositories/lab_backfill.py backend/app/services/lab_service.py backend/app/services/lab_backfill.py backend/alembic/versions/20260731_0012_b8_prioritized_backfill.py backend/tests/unit/test_b8_backfill_schema.py backend/tests/unit/test_b8_backfill_service.py backend/tests/integration/test_b8_backfill_migration.py backend/tests/integration/test_b8_backfill_e2e.py scripts/b8_backfill_dashboard.py tests/test_b8_backfill_dashboard.py --no-cache --no-fix --output-format concise
python -B -m mypy app/models/lab_backfill.py app/repositories/lab_backfill.py app/services/lab_backfill.py --ignore-missing-imports --no-color-output --no-pretty --cache-dir=../output/mypy-cache-b8-final
python -m alembic heads
```

- [ ] **Step 5: Verify recovery and protected state**

Recheck the B8 archive hash and extraction manifest. Verify:

```text
perfume_chem.db
  e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
data/perfumery_kb.db
  5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1
```

Run only read-only URI `PRAGMA quick_check` against the knowledge database.

- [ ] **Step 6: Run final DeepLuna Fast audit**

Run a fresh exact-project check. If `READY`, submit one bounded read-only
FLASH/`NO_LUNA` audit over the design, implementation, tests, migration,
projection, and captured logs. Sol reproduces every finding locally and reruns
affected tests.

- [ ] **Step 7: Write and validate the B8 gate package**

Record exact commits, migration, tests, timings, archive, database hashes,
projection counts, DeepLuna job/cost, defects closed, and residual limits.
Validate JSON, hashes, scoped whitespace, and secret hygiene.

- [ ] **Step 8: Commit the gate package**

Stage only B8 reports/logs/projection and the two migration-head test updates:

```powershell
git commit -m "docs: record Build B8 prioritized backfill gate"
```

Verify the index and every exact B8 path are clean. Only then may B9 begin.
