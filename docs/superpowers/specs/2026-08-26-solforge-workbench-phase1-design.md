# SolForge Workbench Phase 1 Design

**Date:** 2026-08-26

**Status:** Approved architecture; implementation authorized

**Scope:** A local, user-facing shell around the admitted Architectural Delta runtime

**Authority ceiling:** Computational experiment design only. Compounding, inventory
reservation, physical execution, sensory truth, liking, safety, purchase, database
mutation, publication, and release remain unauthorized.

## 1. Decision

Perfume-Chem will expose SolForge as a local staged experiment workbench rather than
as a committee of prompt modules or an autonomous perfumer. Phase 1 assembles the
already admitted deterministic compiler into a usable program without reviving any
failed evidence analyzer.

The program boundary is:

```text
Browser page
  -> bounded FastAPI request
  -> fixed local CLI subprocess
  -> admitted Architectural Delta runtime
  -> atomic hash-bound artifact directory
  -> verified read-only result summary
```

Phase 1 accepts already closed `solforge_case_v1` and
`sol_hypothesis_set_v1` packets. It does not generate hypotheses, reinterpret Sol
prose, or fabricate formula and dose lineage. This is less convenient than a free-text
brief wizard, but it preserves the existing provenance contract. A brief-to-packet
adapter is a later versioned project and cannot be added until absent-build and
absent-dose-receipt semantics are represented honestly.

## 2. Relationship to Existing SolForge Work

This design is an additive application layer over:

- `engine/solforge/runtime.py`;
- `engine/solforge/architectural_adapter.py`;
- the SolForge mode in `scripts/intervention_recommend.py`;
- `configs/complexity/complexity_module_registry_v6.json`; and
- the closed laboratory contexts in `backend/app/schemas/solforge.py`.

It does not change the scientific compiler, registry admission, canonical contract
bytes, or CLI output format.

This document supersedes the user-interface and active evidence-loop assumptions in
`docs/superpowers/specs/2026-08-26-solforge-evidence-loop-design.md` where that older
design expects Temporal Sensory Ledger, Hedonic Preference Learner, or Temporal OAV
Sentinel to participate in runtime. Their source remains compatibility and provenance
code, but fresh V6 benchmark results make them runtime-ineligible.

The older document remains historical provenance. Its target/inventory separation,
hashing, authority, gate, and research constraints remain applicable where they do not
conflict with V6.

## 3. User Outcome

The local application provides:

1. a `/solforge` page linked from the existing laboratory application;
2. a configuration-status panel;
3. two file selectors for a case packet and hypothesis-set packet;
4. one explicit `Compile experiment` action;
5. a result view containing stage, decision, history, blockers, limitations, next
   action, selected intervention, controlled arms, blind codes, inventory statuses,
   registry hash, admitted modules, manifest hash, and record hashes; and
6. a local run identifier for audit and support.

The UI never labels a compiled arm as safe to mix, physically executed, smelled,
preferred, validated, purchasable, or releasable.

## 4. Runtime Inclusion and Exclusion

The Phase 1 runtime may invoke only the module IDs returned by the current admitted
registry. For this API version, the returned set must be exactly:

```text
architectural-delta-engine
```

If the registry returns any other admitted module, the API fails closed with
`RUNTIME_MODULE_SET_CHANGED`. A future capability requires a new API/schema version
and review.

The following remain unreachable from the Workbench:

- Temporal Sensory Ledger;
- Hedonic Preference Learner;
- Temporal OAV Sentinel;
- the retired construction, expansion, citrus, musk, temporal, panel, admission,
  and lifecycle cards;
- the full shadow orchestrator paths that import failed analyzers; and
- legacy aggregate beauty, complexity, hedonic, or OAV authority scores.

## 5. API Contracts

### 5.1 Design request

The endpoint accepts `application/json` only:

```json
{
  "schema_version": "solforge_workbench_design_request_v1",
  "case": {"schema_version": "solforge_case_v1"},
  "hypotheses": {"schema_version": "sol_hypothesis_set_v1"}
}
```

The outer object is closed. Nested packets are passed as JSON objects and are
semantically validated by the existing root CLI contracts. Before subprocess
execution, the backend also verifies:

- exact nested schema versions;
- exact all-false authority mappings on both packets;
- the case inventory path resolves to the configured authoritative inventory path;
- the configured inventory file exists and is a regular non-symlink file;
- the case inventory SHA-256 equals the observed file SHA-256;
- the hypothesis set's `case_sha256` equals the canonical case SHA-256; and
- combined request size does not exceed 524,288 bytes.

Canonical transport JSON uses UTF-8, sorted keys, compact separators, no NaN or
infinity, and no appended newline, matching `engine.evidence_contracts`.

### 5.2 Design response

The response is `solforge_workbench_design_response_v1` and contains only verified
artifact data:

- `run_id`;
- `stage` and `history`;
- `decision`, limitations, and next action;
- blockers;
- registry SHA-256 and admitted module IDs;
- compiled-experiment SHA-256 when present;
- selected hypothesis and delta kind;
- controlled-arm summaries;
- inventory statuses;
- artifact manifest SHA-256 and record summaries;
- `artifact_download_available: false`; and
- the exact all-false authority mapping.

The API does not return server filesystem paths.

### 5.3 Status response

`GET /api/v1/solforge/workbench/status` reports configuration readiness only. It
checks fixed paths, inventory availability, artifact quota, and symlink/path
containment. It does not claim that a future run will compile, that a formula is safe,
or that the scientific registry is admitted beyond the per-run CLI gate.

## 6. Process Boundary

The backend must not import `engine.solforge`.

It invokes the existing CLI with `asyncio.create_subprocess_exec`, never a shell:

```text
<configured-python>
<project-root>/scripts/intervention_recommend.py
--solforge-case <temporary-case-path>
--solforge-hypotheses <temporary-hypothesis-path>
--output-dir <artifact-root>/<server-run-id>
```

All executable, script, project, inventory, and artifact paths come from server
configuration. No request field can supply a command, executable, script, working
directory, inventory override, or output path.

The subprocess:

- runs with `cwd` fixed to the configured project root;
- receives no shell interpolation;
- has a 90-second default timeout;
- captures at most 16,384 characters of diagnostic output for an error response;
- is terminated and awaited on timeout;
- is limited by a process-local semaphore with default capacity one; and
- performs no backend database operation.

## 7. Path and Artifact Security

The configured project root, CLI script, inventory file, and artifact root are
resolved before use. The script and artifact root must remain under the project root.
The inventory file must resolve to the exact configured file. Symlinked configuration
targets fail closed.

Run IDs are generated server-side as `sf-` followed by 32 lowercase hexadecimal
characters. The API never accepts a run ID or output path in a design request.

The CLI already publishes atomically. The backend reads a run only after a zero exit
status and then verifies:

- the run directory is a direct, non-symlink child of the artifact root;
- `MANIFEST.json` is a regular non-symlink file and no larger than 2 MiB;
- every listed record filename is a basename with no path separators;
- every record is a regular non-symlink file inside the run directory;
- every record is no larger than 4 MiB;
- every observed file SHA-256 equals the manifest `file_sha256`;
- record-level authority flags are the exact all-false mapping;
- manifest authority booleans are false;
- the runtime module set is exactly the Phase 1 admitted set; and
- required compiled and decision records are present.

Artifact download is intentionally unavailable in Phase 1. It may be added only with
content-addressed lookup, exact run containment, symlink rejection, response-size
limits, and dedicated traversal tests.

## 8. Quota and Retention

The artifact root is bounded by server configuration:

- maximum completed run directories: 50;
- maximum total artifact bytes: 104,857,600; and
- maximum concurrent runs: one.

Phase 1 performs no automatic destructive cleanup. When either quota is met, status
reports not ready and a design request returns `ARTIFACT_QUOTA_EXCEEDED`. An operator
may archive or remove exact run directories outside the API. Failed atomic CLI runs do
not publish a completed run directory.

This refusal policy prevents unbounded disk use without giving the new API deletion
authority.

## 9. Failure Semantics

| Condition | HTTP/result behavior |
|---|---|
| wrong content type or malformed JSON | `415` or `400` |
| request exceeds byte limit | `413 REQUEST_TOO_LARGE` |
| closed packet preflight fails | `422 PACKET_INVALID` |
| inventory path/hash mismatch | `409 INVENTORY_BINDING_MISMATCH` |
| fixed runtime configuration invalid | `503 WORKBENCH_NOT_CONFIGURED` |
| artifact quota reached | `507 ARTIFACT_QUOTA_EXCEEDED` |
| subprocess timeout | `504 ENGINE_TIMEOUT` |
| subprocess nonzero exit | `422 ENGINE_REJECTED_PACKET` |
| artifact/hash/path validation fails | `502 ARTIFACT_VALIDATION_FAILED` |
| CLI returns `HOLD` | `200`, preserving exact blockers |
| CLI returns `NO_CHANGE` | `200`, successful first-class result |

No error path retries with another provider, script, model, module, inventory, or
output location.

## 10. UI Rules

The page is dependency-free HTML, CSS, and JavaScript consistent with the existing
local laboratory UI.

The browser:

- accepts exactly two `.json` files;
- rejects files larger than 256 KiB each before upload;
- parses JSON locally and displays the nested schema versions;
- disables submission until both packets are present;
- sends one JSON request to the fixed API route;
- renders blockers and limitations before arms;
- renders all authority flags; and
- states that the result is computational experiment design only.

The browser never constructs missing hashes, changes inventory paths, repairs packet
fields, generates a hypothesis, or calls a model.

## 11. Testing

### Unit tests

- closed request and response schemas;
- exact all-false authority enforcement;
- body-size and content-type limits;
- inventory path and hash mismatch;
- hypothesis-to-case hash mismatch;
- fixed executable/script/output arguments with no shell;
- timeout and nonzero-exit handling;
- run ID format;
- quota refusal;
- manifest basename/path containment;
- symlink rejection;
- record-size and hash mismatch;
- exact admitted module set;
- `HOLD`, `NO_CHANGE`, and compiled result rendering; and
- no database service import or write path.

### Integration tests

- API dependency replacement with a real artifact-verification fixture;
- status and design routes through ASGI;
- static `/solforge` page and required assets;
- a focused real-CLI smoke using the existing SolForge packet fixtures and a
  temporary authoritative workbook; and
- unchanged existing SolForge runtime-isolation and CLI tests.

### Verification order

1. focused backend schema/service tests;
2. backend Ruff;
3. backend mypy;
4. focused backend API/static tests;
5. focused root SolForge runtime/CLI tests;
6. quick project verification; and
7. full project verification before merge or publication.

## 12. Phase 1 Acceptance

Phase 1 is accepted when:

- a user can open `/solforge`, select two valid closed packets, and receive the
  verified experiment summary without editing JSON;
- valid `NO_CHANGE`, `HOLD`, and compiled cases remain distinguishable;
- no request-controlled filesystem or command path reaches the subprocess;
- every returned artifact hash is independently verified;
- only `architectural-delta-engine` is reachable;
- all authority flags remain false;
- no laboratory or database record is written;
- focused tests, lint, type checks, and declared project verification pass; and
- the branch contains a reviewable commit with no generated run artifacts.

Phase 1 acceptance does not establish superiority over Sol xhigh. It establishes a
safe program shell around the already admitted deterministic capability. New evidence
modules still require fresh blinded comparison against plain Sol xhigh and the
length-matched control before a later Workbench version can invoke them.

## 13. Deferred Work

The following are separate, versioned projects:

1. a provenance-safe brief-to-packet Sol adapter;
2. laboratory persistence of an explicitly approved experiment;
3. Protocol Integrity Gate;
4. observed-only Temporal Change Analyzer;
5. criterion-specific evidence learning;
6. content-addressed artifact downloads;
7. background job persistence and recovery; and
8. desktop packaging.

None is implicitly authorized by Phase 1.
