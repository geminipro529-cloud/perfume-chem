# SolForge Workbench Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free local Workbench page and bounded FastAPI bridge that run the already admitted Architectural Delta CLI from closed SolForge packets and return a verified, all-false-authority experiment summary.

**Architecture:** The backend never imports `engine.solforge`; it validates transport-level invariants, writes canonical temporary packet files, invokes the existing `scripts/intervention_recommend.py` CLI with fixed configured paths through `asyncio.create_subprocess_exec`, and verifies every emitted artifact before responding. The browser only selects two closed JSON packets and renders the verified result. No database or laboratory mutation occurs.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, asyncio subprocesses, pytest/pytest-asyncio, dependency-free HTML/CSS/JavaScript, existing root SolForge CLI.

**Spec:** `docs/superpowers/specs/2026-08-26-solforge-workbench-phase1-design.md`

## Global Constraints

- The API may invoke only `architectural-delta-engine` for this schema version.
- The backend must not import `engine.solforge`.
- Inputs are existing `solforge_case_v1` and `sol_hypothesis_set_v1` packets; the API generates neither.
- Request-controlled commands, executable paths, inventory paths, working directories, run IDs, and output paths are forbidden.
- The combined JSON request limit is 524,288 bytes.
- Subprocess timeout is 90 seconds and default concurrency is one.
- Completed artifacts are limited to 50 runs and 104,857,600 bytes; the API performs no deletion.
- Artifact download is unavailable in Phase 1.
- Every compounding, hedonic, physical-execution, purchase, release, safety, and sensory authority flag remains false.
- No backend database or laboratory persistence call is permitted.
- Root and backend environments communicate only through canonical JSON files and the existing CLI.

---

### Task 1: Closed Workbench schemas and fixed server configuration

**Files:**
- Create: `backend/app/schemas/solforge_workbench.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_solforge_workbench_schemas.py`

**Interfaces:**
- Consumes: Pydantic `BaseModel`, existing `Settings` and project-root resolution.
- Produces: `SolForgeWorkbenchDesignRequestV1`, `SolForgeWorkbenchDesignResponseV1`, `SolForgeWorkbenchStatusV1`, `ArtifactRecordSummaryV1`, `ArmSummaryV1`, and fixed `SOLFORGE_*` settings.

- [ ] **Step 1: Write failing closed-schema tests**

```python
from pydantic import ValidationError

from app.schemas.solforge_workbench import SolForgeWorkbenchDesignRequestV1

FALSE_FLAGS = {
    "compounding": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


def test_design_request_accepts_only_closed_packets(case_packet, hypothesis_packet):
    parsed = SolForgeWorkbenchDesignRequestV1.model_validate(
        {
            "schema_version": "solforge_workbench_design_request_v1",
            "case": case_packet,
            "hypotheses": hypothesis_packet,
        }
    )
    assert parsed.case["authority_flags"] == FALSE_FLAGS


def test_design_request_rejects_true_authority(case_packet, hypothesis_packet):
    case_packet["authority_flags"]["sensory"] = True
    with pytest.raises(ValidationError):
        SolForgeWorkbenchDesignRequestV1.model_validate(
            {
                "schema_version": "solforge_workbench_design_request_v1",
                "case": case_packet,
                "hypotheses": hypothesis_packet,
            }
        )
```

- [ ] **Step 2: Run the schema tests and confirm import failure**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_schemas.py -q`

Expected: collection fails because `app.schemas.solforge_workbench` does not exist.

- [ ] **Step 3: Implement the exact models**

```python
class SolForgeWorkbenchDesignRequestV1(_ClosedModel):
    schema_version: Literal["solforge_workbench_design_request_v1"]
    case: dict[str, Any]
    hypotheses: dict[str, Any]

    @model_validator(mode="after")
    def validate_packets(self):
        if self.case.get("schema_version") != "solforge_case_v1":
            raise ValueError("case must be solforge_case_v1")
        if self.hypotheses.get("schema_version") != "sol_hypothesis_set_v1":
            raise ValueError("hypotheses must be sol_hypothesis_set_v1")
        for packet in (self.case, self.hypotheses):
            if packet.get("authority_flags") != AUTHORITY_FLAGS_FALSE:
                raise ValueError("packet authority_flags must be the exact all-false mapping")
        return self
```

Define response/status models with `ConfigDict(extra="forbid", frozen=True)` and typed arm, artifact, inventory-status, history, blocker, decision, and authority fields.

Add these settings to `Settings`:

```python
SOLFORGE_ENGINE_PYTHON: str = sys.executable
SOLFORGE_PROJECT_ROOT: str = str(PROJECT_ROOT)
SOLFORGE_INVENTORY_PATH: str = str(
    PROJECT_ROOT / "Kenny_Current_Perfumery_Inventory_Master_Aug2026_v5.xlsx"
)
SOLFORGE_ARTIFACT_ROOT: str = str(PROJECT_ROOT / "output" / "solforge-workbench")
SOLFORGE_TIMEOUT_SECONDS: int = 90
SOLFORGE_MAX_BODY_BYTES: int = 524_288
SOLFORGE_MAX_RUNS: int = 50
SOLFORGE_MAX_ARTIFACT_BYTES: int = 104_857_600
SOLFORGE_MAX_RECORD_BYTES: int = 4_194_304
SOLFORGE_MAX_CONCURRENT_RUNS: int = 1
```

- [ ] **Step 4: Run schema tests**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_schemas.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the schema boundary**

```powershell
git add backend/app/schemas/solforge_workbench.py backend/app/core/config.py backend/tests/test_solforge_workbench_schemas.py
git commit -m "feat(solforge): define workbench transport contracts"
```

### Task 2: Packet, path, quota, and artifact verification service

**Files:**
- Create: `backend/app/services/solforge_workbench.py`
- Test: `backend/tests/test_solforge_workbench_service.py`

**Interfaces:**
- Consumes: Task 1 request/response models and `Settings`.
- Produces: `WorkbenchFailure`, `WorkbenchRuntimeConfig`, `canonical_json_bytes`, `validate_packet_binding`, `inspect_artifact_quota`, `verify_artifact_run`, and `SolForgeWorkbenchService`.

- [ ] **Step 1: Write failing pure-boundary tests**

```python
def test_packet_binding_rejects_inventory_path_override(runtime_config, request_packet):
    request_packet.case["inventory_path"] = str(runtime_config.project_root / "other.xlsx")
    with pytest.raises(WorkbenchFailure, match="INVENTORY_BINDING_MISMATCH"):
        validate_packet_binding(request_packet, runtime_config)


def test_packet_binding_rejects_case_hash_mismatch(runtime_config, request_packet):
    request_packet.hypotheses["case_sha256"] = "f" * 64
    with pytest.raises(WorkbenchFailure, match="PACKET_INVALID"):
        validate_packet_binding(request_packet, runtime_config)


def test_artifact_verifier_rejects_parent_path(runtime_config, valid_run):
    manifest = json.loads((valid_run / "MANIFEST.json").read_text())
    manifest["records"][0]["filename"] = "../escape.json"
    (valid_run / "MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises(WorkbenchFailure, match="ARTIFACT_VALIDATION_FAILED"):
        verify_artifact_run(valid_run, runtime_config)


def test_artifact_verifier_rejects_hash_mismatch(runtime_config, valid_run):
    record = next(valid_run.glob("decision_receipt_v1--*.json"))
    record.write_bytes(b"{}")
    with pytest.raises(WorkbenchFailure, match="ARTIFACT_VALIDATION_FAILED"):
        verify_artifact_run(valid_run, runtime_config)
```

- [ ] **Step 2: Run service tests and confirm missing-module failure**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_service.py -q`

Expected: collection fails because the service module does not exist.

- [ ] **Step 3: Implement fixed runtime configuration and pure validation**

```python
@dataclass(frozen=True, slots=True)
class WorkbenchRuntimeConfig:
    engine_python: Path
    project_root: Path
    script_path: Path
    inventory_path: Path
    artifact_root: Path
    timeout_seconds: int
    max_runs: int
    max_artifact_bytes: int
    max_record_bytes: int


def validate_packet_binding(
    request: SolForgeWorkbenchDesignRequestV1,
    config: WorkbenchRuntimeConfig,
) -> tuple[bytes, bytes]:
    case_bytes = canonical_json_bytes(request.case)
    hypotheses_bytes = canonical_json_bytes(request.hypotheses)
    observed_case_sha256 = hashlib.sha256(case_bytes).hexdigest()
    if Path(str(request.case["inventory_path"])).resolve() != config.inventory_path:
        raise WorkbenchFailure("INVENTORY_BINDING_MISMATCH", 409, "...")
    if sha256_file(config.inventory_path) != request.case.get("inventory_sha256"):
        raise WorkbenchFailure("INVENTORY_BINDING_MISMATCH", 409, "...")
    if request.hypotheses.get("case_sha256") != observed_case_sha256:
        raise WorkbenchFailure("PACKET_INVALID", 422, "...")
    return case_bytes, hypotheses_bytes
```

Implement `resolve_runtime_config` with regular-file, non-symlink, and resolved-path
containment checks. Implement quota inspection without deleting files. Implement
artifact verification using basename-only filenames, direct-child containment,
non-symlink regular files, size limits, SHA-256 checks, exact all-false flags, and
exact admitted module set `("architectural-delta-engine",)`.

- [ ] **Step 4: Run the service tests**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_service.py -q`

Expected: all pure validation and artifact tests pass.

- [ ] **Step 5: Commit the verification boundary**

```powershell
git add backend/app/services/solforge_workbench.py backend/tests/test_solforge_workbench_service.py
git commit -m "feat(solforge): verify workbench packets and artifacts"
```

### Task 3: Bounded asynchronous CLI execution

**Files:**
- Modify: `backend/app/services/solforge_workbench.py`
- Modify: `backend/tests/test_solforge_workbench_service.py`

**Interfaces:**
- Consumes: Task 2 validators and exact root CLI contract.
- Produces: `SolForgeWorkbenchService.status()` and `SolForgeWorkbenchService.run_design()`.

- [ ] **Step 1: Write failing runner tests**

```python
@pytest.mark.asyncio
async def test_runner_uses_fixed_argv_without_shell(service, request_packet, monkeypatch):
    observed = {}

    async def fake_create_subprocess_exec(*argv, **kwargs):
        observed["argv"] = argv
        observed["kwargs"] = kwargs
        return CompletedFakeProcess(returncode=0)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    await service.run_design(request_packet)
    assert observed["argv"][0] == str(service.config.engine_python)
    assert observed["argv"][1] == str(service.config.script_path)
    assert "shell" not in observed["kwargs"]
    assert observed["kwargs"]["cwd"] == str(service.config.project_root)


@pytest.mark.asyncio
async def test_runner_maps_timeout_to_engine_timeout(service, request_packet, monkeypatch):
    monkeypatch.setattr(asyncio, "wait_for", raise_timeout)
    with pytest.raises(WorkbenchFailure, match="ENGINE_TIMEOUT"):
        await service.run_design(request_packet)
```

- [ ] **Step 2: Run the runner tests and confirm behavioral failure**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_service.py -k runner -q`

Expected: tests fail because the service has no runner implementation.

- [ ] **Step 3: Implement async execution and status**

```python
async def _run_cli(self, case_path: Path, hypotheses_path: Path, run_dir: Path):
    process = await asyncio.create_subprocess_exec(
        str(self.config.engine_python),
        str(self.config.script_path),
        "--solforge-case", str(case_path),
        "--solforge-hypotheses", str(hypotheses_path),
        "--output-dir", str(run_dir),
        cwd=str(self.config.project_root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=self.config.timeout_seconds
        )
    except TimeoutError:
        process.kill()
        await process.wait()
        raise WorkbenchFailure("ENGINE_TIMEOUT", 504, "SolForge CLI timed out")
    if process.returncode != 0:
        detail = (stderr or stdout).decode("utf-8", errors="replace")[-16_384:]
        raise WorkbenchFailure("ENGINE_REJECTED_PACKET", 422, detail)
```

`run_design` acquires the process-local semaphore, refuses quota exhaustion, creates
temporary canonical input files under the artifact root, generates the run ID, invokes
the CLI, verifies the completed run, and returns the typed response. `status` performs
configuration and quota checks without invoking the CLI.

- [ ] **Step 4: Run all service tests**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_service.py -q`

Expected: all tests pass, including timeout, nonzero exit, quota, and fixed argv.

- [ ] **Step 5: Commit execution support**

```powershell
git add backend/app/services/solforge_workbench.py backend/tests/test_solforge_workbench_service.py
git commit -m "feat(solforge): execute admitted workbench CLI safely"
```

### Task 4: FastAPI status and design endpoints

**Files:**
- Create: `backend/app/api/v1/endpoints/solforge_workbench.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_solforge_workbench_api.py`

**Interfaces:**
- Consumes: `SolForgeWorkbenchService`, Task 1 schemas, FastAPI `Request` streaming.
- Produces: `GET /api/v1/solforge/workbench/status` and `POST /api/v1/solforge/workbench/design`.

- [ ] **Step 1: Write failing API tests**

```python
@pytest.mark.asyncio
async def test_design_rejects_non_json(client):
    response = await client.post(
        "/api/v1/solforge/workbench/design",
        content=b"not json",
        headers={"content-type": "text/plain"},
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_design_rejects_oversized_body(client):
    response = await client.post(
        "/api/v1/solforge/workbench/design",
        content=b"x" * 524_289,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_design_returns_verified_service_result(client, app, fake_service):
    app.dependency_overrides[get_solforge_workbench_service] = lambda: fake_service
    response = await client.post("/api/v1/solforge/workbench/design", json=valid_request())
    assert response.status_code == 200
    assert response.json()["artifact_download_available"] is False
    assert not any(response.json()["authority_flags"].values())
```

- [ ] **Step 2: Run API tests and confirm 404 failures**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_api.py -q`

Expected: status/design tests fail with 404 because the router is absent.

- [ ] **Step 3: Implement bounded body streaming and route error mapping**

```python
async def _read_bounded_json(request: Request, limit: int) -> object:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail={"code": "JSON_REQUIRED"})
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > limit:
            raise HTTPException(status_code=413, detail={"code": "REQUEST_TOO_LARGE"})
    try:
        return json.loads(chunks.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail={"code": "MALFORMED_JSON"}) from exc
```

Validate with `SolForgeWorkbenchDesignRequestV1.model_validate`, call the service,
and map `WorkbenchFailure.status_code` and code without changing its meaning. Register
the router under `/solforge/workbench`.

- [ ] **Step 4: Run API tests**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_api.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the API**

```powershell
git add backend/app/api/v1/endpoints/solforge_workbench.py backend/app/api/v1/router.py backend/tests/test_solforge_workbench_api.py
git commit -m "feat(solforge): expose bounded workbench API"
```

### Task 5: Dependency-free Workbench page

**Files:**
- Create: `backend/app/static/solforge.html`
- Create: `backend/app/static/solforge.css`
- Create: `backend/app/static/solforge.js`
- Modify: `backend/app/static/index.html`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_solforge_workbench_static.py`

**Interfaces:**
- Consumes: Task 4 status/design endpoints.
- Produces: `/solforge` page with local packet selection and result rendering.

- [ ] **Step 1: Write failing static-surface tests**

```python
@pytest.mark.asyncio
async def test_solforge_page_is_served(client):
    response = await client.get("/solforge")
    assert response.status_code == 200
    assert 'id="case-file"' in response.text
    assert 'id="hypotheses-file"' in response.text
    assert 'id="compile-experiment"' in response.text
    assert "Computational experiment design only" in response.text


def test_javascript_has_client_file_limit():
    script = (STATIC_DIR / "solforge.js").read_text(encoding="utf-8")
    assert "262144" in script
    assert "artifact_download_available" in script
    assert "authority_flags" in script
```

- [ ] **Step 2: Run static tests and confirm missing-page failure**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_static.py -q`

Expected: `/solforge` returns 404 and assets are missing.

- [ ] **Step 3: Implement the page and static route**

Add to `backend/app/main.py`:

```python
@app.get("/solforge", response_class=FileResponse)
async def solforge_workbench_app():
    return STATIC_DIR / "solforge.html"
```

The JavaScript stores parsed packet objects only in memory, enforces 262,144 bytes per
file, fetches status on load, posts the closed request, renders blockers/limitations
before arms, lists hashes and false authority flags, and never offers download or
physical-execution actions. Add a visible Workbench link to the current app.

- [ ] **Step 4: Run static and API tests**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_static.py tests/test_solforge_workbench_api.py -q`

Expected: all tests pass.

- [ ] **Step 5: Commit the UI**

```powershell
git add backend/app/static/solforge.html backend/app/static/solforge.css backend/app/static/solforge.js backend/app/static/index.html backend/app/main.py backend/tests/test_solforge_workbench_static.py
git commit -m "feat(solforge): add local experiment workbench"
```

### Task 6: Real-CLI smoke, regression verification, and branch handoff

**Files:**
- Test: `backend/tests/test_solforge_workbench_real_cli.py`
- Verify: existing root and backend suites named below

**Interfaces:**
- Consumes: Tasks 1-5 and existing root SolForge fixture/CLI contracts.
- Produces: one focused real-process proof plus final verification evidence; no committed generated artifacts.

- [ ] **Step 1: Write a real-CLI smoke using temporary inputs and artifacts**

```python
@pytest.mark.asyncio
async def test_real_cli_compiles_no_change_case(tmp_path, configured_service, packets):
    response = await configured_service.run_design(packets.no_change)
    assert response.stage == "DECIDED"
    assert response.decision == "NO_CHANGE"
    assert response.admitted_module_ids == ("architectural-delta-engine",)
    assert not any(response.authority_flags.values())
```

The fixture must copy or create the authoritative workbook used by existing
Architectural Delta tests, bind its exact SHA-256 in the case, and use the current
interpreter and existing CLI. It must not call a model, network, database, or physical
laboratory service.

- [ ] **Step 2: Run the smoke and focused backend suite**

Run: `cd backend; poetry run pytest tests/test_solforge_workbench_schemas.py tests/test_solforge_workbench_service.py tests/test_solforge_workbench_api.py tests/test_solforge_workbench_static.py tests/test_solforge_workbench_real_cli.py -q`

Expected: all tests pass.

- [ ] **Step 3: Run backend quality gates in repository order**

Run:

```powershell
cd backend
poetry run ruff check app tests/test_solforge_workbench_schemas.py tests/test_solforge_workbench_service.py tests/test_solforge_workbench_api.py tests/test_solforge_workbench_static.py tests/test_solforge_workbench_real_cli.py
poetry run mypy app --ignore-missing-imports
poetry run pytest tests/test_solforge_workbench_schemas.py tests/test_solforge_workbench_service.py tests/test_solforge_workbench_api.py tests/test_solforge_workbench_static.py tests/test_solforge_workbench_real_cli.py -q
```

Expected: each command exits zero.

- [ ] **Step 4: Run existing root SolForge regressions**

Run:

```powershell
pytest tests/test_intervention_recommend_solforge.py tests/test_solforge_architectural_adapter.py tests/test_solforge_runtime_isolation.py tests/test_complexity_registry_v6.py -q
```

Expected: each selected test passes and failed evidence analyzers remain unreachable.

- [ ] **Step 5: Run project verification**

Run: `python scripts/pipeline_audit.py project-verify --quick --json`

If quick verification is clean at its declared scope, run:

`python scripts/pipeline_audit.py project-verify --json`

Record exact pass, skip, and failure counts. Do not convert a partial or blocked check
into a passing claim.

- [ ] **Step 6: Inspect the final diff and generated-artifact boundary**

Run:

```powershell
git status --short
git diff --check
git diff --stat
git diff -- backend/app backend/tests docs/superpowers
```

Confirm no `output/solforge-workbench` run, packet upload, workbook, database, secret,
or temporary file is staged.

- [ ] **Step 7: Obtain one bounded DeepLuna diff-risk review**

Run a fresh exact-project health check. If and only if readiness is `READY`, submit a
read-only, repository-relative, line-bounded review of the new backend service, endpoint,
and tests. Treat the result as advisory and verify every accepted finding locally.

- [ ] **Step 8: Commit and push the verified Phase 1 slice**

```powershell
git add docs/superpowers/specs/2026-08-26-solforge-workbench-phase1-design.md docs/superpowers/plans/2026-08-26-solforge-workbench-phase1.md backend/app backend/tests
git commit -m "feat(solforge): assemble phase one workbench"
git push origin codex/complex-perfumery-publish
```

After the push, verify the remote branch resolves to the local commit before reporting
GitHub handoff.
