# Build B9 science reporting implementation plan

> Execute in strict order with focused red-green tests, exact staging, and a
> verified gate before B10.

**Goal:** Expose B1-B7 authority through a safe, deterministic JSON API,
Markdown report, and dependency-free local UI while preserving all eight
evidence classes and separating strict from exploratory use without hiding
unknowns.

**Architecture:** Add a read-only repository and projection service over the
existing append-only models. The canonical JSON report uses explicit field
allowlists and code-owned strict predicates. Markdown and UI consume the same
report contract. No migration or production write path is added.

**Runtime:** Python 3.11.15 from
`output/verification-envs/a2-slice2-py311/Scripts/python.exe`, FastAPI,
SQLAlchemy async, Pydantic v2, vanilla JavaScript, and local CSS.

**Design:** `docs/superpowers/specs/2026-07-31-build-b9-science-reporting-design.md`

## Fixed safety constraints

- Do not read or expose secrets, environment values, or unrestricted model
  columns.
- Do not serialize `preserved_artifact_path`, `raw_source_path`, database
  paths, or source wording that is unnecessary for the authority report.
- Do not add a confidence or coverage percentage.
- Do not infer scientific authority from row presence.
- Strict-negative decisions such as `BLOCK` or regulatory `FAIL` remain
  strict-eligible when their canonical decision is authoritative.
- Unknown, heuristic, speculative, rejected, and conflicted records remain
  visible in strict mode under `withheld`.
- No migration and no B1-B8 data mutation.
- Preserve all unrelated tracked and untracked work.

## Task 1: Freeze the response vocabulary and pure projection contract

**Files:**

- Create: `backend/app/schemas/lab_reporting.py`
- Create: `backend/app/services/lab_reporting.py`
- Create: `backend/tests/unit/test_b9_science_reporting.py`

- [ ] **Step 1: Write RED schema and pure-policy tests**

Cover:

- exact eight-label order;
- exact twenty-section order;
- strict and exploratory view literals;
- report and section count reconciliation;
- recursive absence of confidence/coverage/overall-score keys;
- recursive absence of blocked local-path fields;
- source-type evidence mapping;
- direct evidence-class preservation;
- conservative `UNKNOWN` fallback;
- strict-negative `BLOCK` eligibility;
- unresolved conflict withholding;
- strict mode retaining withheld records;
- exploratory mode including the same records without relabeling;
- exact-locator requirement;
- stable `(created_at, id)` ordering;
- canonical JSON hash determinism; and
- deterministic Markdown rendering.

Run:

```powershell
python -m pytest tests/unit/test_b9_science_reporting.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-unit-red
```

Expected: fail because B9 modules do not exist.

- [ ] **Step 2: Implement strict response schemas**

Define:

- `SCIENCE_EVIDENCE_CLASSES`;
- `SCIENCE_SECTION_KEYS`;
- `ScienceView`;
- `ScienceRecord`;
- `ScienceSection`;
- `ScienceReportPolicy`;
- `ScienceAuthorityReport`; and
- strict `extra="forbid"` response validation.

No schema field may be named like an aggregate confidence or coverage score.

- [ ] **Step 3: Implement pure projection helpers**

Implement:

- JSON-safe value normalization;
- code-owned evidence-class mapping;
- per-section strict predicates;
- conservative linked evidence inheritance;
- explicit safe-field and provenance allowlists;
- required-locator checks;
- section partitioning;
- recursive banned-key and blocked-field enforcement;
- canonical report hashing; and
- deterministic Markdown rendering.

Keep database access out of these helpers.

- [ ] **Step 4: Run unit GREEN**

```powershell
python -m pytest tests/unit/test_b9_science_reporting.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-unit-green
```

- [ ] **Step 5: Commit the pure contract**

```powershell
git add backend/app/schemas/lab_reporting.py backend/app/services/lab_reporting.py backend/tests/unit/test_b9_science_reporting.py
git commit -m "feat: define Build B9 science report contract"
```

## Task 2: Query and project canonical B1-B7 authority

**Files:**

- Create: `backend/app/repositories/lab_reporting.py`
- Modify: `backend/app/services/lab_reporting.py`
- Modify: `backend/tests/unit/test_b9_science_reporting.py`

- [ ] **Step 1: Write RED repository/service tests**

Use a bounded fake repository to prove:

- every required model collection is requested once;
- parent/link maps are constructed by exact IDs;
- source, observation, assertion, conflict, threshold, analytical,
  regulatory, and claim sections are populated;
- extraction workflow state uses the latest sequence event;
- blocking rule contradictions withhold rules;
- claim support inherits strict eligibility only from its exact parent claim;
- no N+1 lazy-loading assumptions occur; and
- report bytes and hash are stable under input-order permutation.

- [ ] **Step 2: Implement the read-only repository**

Query explicit models in stable order. The repository API returns typed
collections only and exposes no write methods.

Models:

- B1 source documents, extractions, and workflow events;
- B2 observations, conflicts/members, selected assertions/candidates;
- B3 threshold contexts and OAV assessments;
- B4 knowledge rules and contradictions;
- B5 methods, validations, sequences, sequence entries, runs, peaks, GC-O
  events, and analytical claim assessments;
- B6 regulatory snapshots and findings; and
- B7 claim decisions and support links.

- [ ] **Step 3: Implement cross-record projection**

Build exact maps for:

- source version to source class/review state;
- extraction to latest workflow state;
- observation to evidence class/strict state;
- selected assertion to selected observation;
- conflict set to members;
- threshold context and OAV to linked assertions/observations;
- rule to blocking contradictions;
- method to validation state;
- run/peak/GC-O to exact parents;
- regulatory finding to snapshot; and
- claim support to parent claim.

Unknown or broken linkage must remain visible and strict-withheld with a
specific reason code.

- [ ] **Step 4: Run focused unit tests**

```powershell
python -m pytest tests/unit/test_b9_science_reporting.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-service-green
```

- [ ] **Step 5: Commit repository projection**

```powershell
git add backend/app/repositories/lab_reporting.py backend/app/services/lab_reporting.py backend/tests/unit/test_b9_science_reporting.py
git commit -m "feat: project canonical Build B science authority"
```

## Task 3: Expose JSON and Markdown API routes

**Files:**

- Create: `backend/app/api/v1/endpoints/lab_reporting.py`
- Modify: `backend/app/api/v1/router.py`
- Create: `backend/tests/integration/test_b9_science_reporting_api.py`

- [ ] **Step 1: Write API RED tests**

Cover:

- `/api/v1/lab/science/authority?view=strict`;
- `/api/v1/lab/science/authority?view=exploratory`;
- `/api/v1/lab/science/report.md?view=strict`;
- invalid view rejected by validation;
- exact schema version, mode, authority statement, labels, twenty sections,
  counts, and 64-character report digest;
- reviewed source and exact locator round trip;
- accepted measured observation included in strict;
- heuristic/speculative/unknown record present but withheld in strict;
- same record included in exploratory with unchanged label;
- unresolved conflict remains visible;
- authoritative `BLOCK` decision included in strict;
- no recursive aggregate confidence key;
- no recursive blocked local-path field;
- Markdown content type, deterministic bytes, exact locator, evidence label,
  and no confidence percentage; and
- repeated GETs do not alter table counts.

Use canonical B1/B2/B7 services or explicit valid model fixtures; do not
weaken constraints for test setup.

- [ ] **Step 2: Add endpoints**

The endpoint module accepts only `ScienceView`, delegates to the read-only
service, and returns:

- Pydantic-validated JSON; or
- UTF-8 `text/markdown` generated from that JSON.

It does not accept POST, PATCH, PUT, or DELETE.

- [ ] **Step 3: Register the router**

Mount under:

```text
/api/v1/lab/science
```

Keep the existing `/api/v1/lab` routes unchanged.

- [ ] **Step 4: Run API GREEN**

```powershell
python -m pytest tests/integration/test_b9_science_reporting_api.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-api-green
```

- [ ] **Step 5: Run existing lab API compatibility**

```powershell
python -m pytest tests/integration/test_lab_api.py tests/integration/test_api_endpoints.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-api-compat
```

- [ ] **Step 6: Commit API**

```powershell
git add backend/app/api/v1/endpoints/lab_reporting.py backend/app/api/v1/router.py backend/tests/integration/test_b9_science_reporting_api.py
git commit -m "feat: expose Build B9 science authority API"
```

## Task 4: Add the local science-authority UI

**Files:**

- Modify: `backend/app/static/index.html`
- Modify: `backend/app/static/lab.js`
- Modify: `backend/app/static/lab.css`
- Modify: `backend/tests/integration/test_lab_ui.py`

- [ ] **Step 1: Write UI RED assertions**

Assert:

- `data-view="science"` and matching panel;
- strict/exploratory controls;
- all eight exact evidence labels in the page;
- explicit non-promoting and unknown-visible wording;
- included and withheld containers;
- JSON and Markdown report actions;
- JavaScript requests the canonical authority endpoint;
- JavaScript renders evidence classes and strict reason codes;
- JavaScript uses escaping or `textContent` for record values;
- no `innerHTML` path accepts unescaped record-provided text;
- no confidence percentage language; and
- mobile/reduced-motion support remains present.

- [ ] **Step 2: Add semantic HTML**

Add one navigation item and a science panel containing:

- view controls;
- eight-class legend;
- policy statement;
- summary counts;
- report downloads; and
- section container.

- [ ] **Step 3: Add safe JavaScript rendering**

Load the report only when entering or refreshing the science view. Render
record text through `escapeHtml` or DOM `textContent`. Preserve all evidence
labels exactly and make strict-withheld records visually explicit.

- [ ] **Step 4: Add evidence-class styles**

Use distinct badge classes for all eight labels and separate included versus
withheld panels. Maintain responsive and reduced-motion behavior.

- [ ] **Step 5: Run UI and API tests**

```powershell
python -m pytest tests/integration/test_lab_ui.py tests/integration/test_b9_science_reporting_api.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-ui-green
```

- [ ] **Step 6: Commit UI**

```powershell
git add backend/app/static/index.html backend/app/static/lab.js backend/app/static/lab.css backend/tests/integration/test_lab_ui.py
git commit -m "feat: add Build B9 science authority UI"
```

## Task 5: Run the B9 gate and record evidence

**Files:**

- Create: `docs/verification/b9/science_reporting_gate.md`
- Create: `docs/verification/b9/science_reporting_gate.json`
- Create: `docs/verification/b9/logs/*`

- [ ] **Step 1: Run exact B9 tests**

```powershell
python -m pytest tests/unit/test_b9_science_reporting.py tests/integration/test_b9_science_reporting_api.py tests/integration/test_lab_ui.py --color=no -q --basetemp=../output/pytest-temp-backend/b9-exact-final
```

- [ ] **Step 2: Run A2 through B9 compatibility**

Run the complete A2 and B1-B9 schema/service/migration/e2e set plus canonical
lab API, UI, migration, export/import, and backup/restore tests. Use no PTY,
no ANSI, captured stdout/stderr, and a 15-minute timeout.

- [ ] **Step 3: Run static gates**

```powershell
python -m ruff check backend/app/schemas/lab_reporting.py backend/app/repositories/lab_reporting.py backend/app/services/lab_reporting.py backend/app/api/v1/endpoints/lab_reporting.py backend/app/api/v1/router.py backend/tests/unit/test_b9_science_reporting.py backend/tests/integration/test_b9_science_reporting_api.py backend/tests/integration/test_lab_ui.py --no-cache --no-fix --output-format concise --color never
python -B -m mypy app/schemas/lab_reporting.py app/repositories/lab_reporting.py app/services/lab_reporting.py app/api/v1/endpoints/lab_reporting.py --ignore-missing-imports --no-color-output --no-pretty --cache-dir=../output/mypy-cache-b9-final
python -m alembic heads
```

- [ ] **Step 4: Verify reporting invariants**

Programmatically inspect strict and exploratory outputs from a temporary
migrated database:

- every required section and label present;
- section/totals reconciliation;
- unknowns visible;
- strict-negative decisions included;
- no aggregate confidence/coverage key;
- no blocked local-path field;
- report hashes deterministic;
- Markdown deterministic; and
- GET requests leave all table counts unchanged.

- [ ] **Step 5: Verify recovery and protected state**

Recheck the B9 archive and protected database hashes. Run only immutable
read-only `PRAGMA quick_check` against the knowledge database.

- [ ] **Step 6: Run final DeepLuna Fast audit**

Run a fresh exact-project check. If `READY`, submit one bounded read-only
FLASH/`NO_LUNA` audit over the design, implementation, tests, UI, reports,
and captured logs. Sol reproduces every material finding locally.

- [ ] **Step 7: Write and validate the B9 gate package**

Record exact commits, routes, sections, evidence labels, tests and timings,
archive, protected hashes, deterministic report evidence, DeepLuna job/cost,
closed defects, and residual limits. Validate JSON, scoped whitespace, log
digests, ANSI absence, and secret hygiene.

- [ ] **Step 8: Commit the gate package**

```powershell
git add docs/verification/b9
git commit -m "docs: record Build B9 science reporting gate"
```

Verify the index and every exact B9 path are clean. Only then may B10 begin.
