# DeepLuna Chat Project Scheduler Spec-Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task with review
> checkpoints. Never use Codex subagents in this project.

**Goal:** Build and verify an immutable V2 DeepLuna Chat runtime that closes
the accepted project-scheduler specification while preserving the active V1
runtime as the rollback target.

**Architecture:** Extend the daemon and SQLite store as the sole scheduling
authority. Keep 128 authenticated pipe connections, 50 logical readers, and 10
path-isolated writers, but introduce a distinct canary-derived paid-provider
window. Replace origin-bearing producer identity and in-memory parallel writer
ownership with cross-origin subscriber isolation and durable scope-aware writer
queueing. Reduce the host CLI to a thin submit/status/reattach client.

**Tech Stack:** Node.js ES modules, `node:test`, SQLite through the existing
runtime binding, Windows named pipes, PowerShell build/verification scripts,
Python `unittest`/pytest for host isolation checks, SHA-256 manifests.

## Global Constraints

- Exact project: `perfume-chem-cheapluna-isolated`.
- Exact route: `cheapluna-chat / DIRECT_PRO / NO_LUNA`.
- DeepLuna Fast, DeepInfra, Luna, Codex orchestration, and alternate fallback
  remain disabled.
- Sol remains architecture, security, science, provenance, release,
  paid-concurrency, and final-acceptance authority.
- Automatic admission applies only to authenticated validated reads and fully
  scoped, reversible, non-conflicting writes.
- Scientific, physical, package-promotion, release, destructive, credential,
  and irreversible authority remain manual.
- Do not mutate an installed immutable runtime. Build a new V2 candidate and
  preserve build
  `5756cbcfa419c2db7b9529639e905767af6ca5d80ff1e723bde1c688d19f7e25`
  as rollback.
- Pipe connections remain 128; logical limits remain 50 readers and 10 path-isolated writers.
  These limits never imply paid-provider concurrency.
- The daemon and SQLite ledger are the sole scheduling authority; clients do
  not own queue, lease, dependency, single-flight, or accounting truth.
- V2 paid-provider concurrency defaults to one and can increase only to a
  separately accepted clean canary stage.
- Every provider transmission must be durably reserved before dispatch and
  reconciled exactly once. Unknown state blocks further project transmissions.
- A client timeout is ambiguous and must never trigger automatic resubmission.
- Any `STALE_ATTEMPT_LEASE` recurrence stops the canary or activation gate.
- Implement in an isolated Git worktree. Seed only the exact current bytes
  listed below; never modify the dirty primary workspace during engineering.
- Use test-driven development: demonstrate the expected failure before each
  behavior change, then run the focused and related suites.
- Provider-free verification uses the real named pipe and deterministic local
  mock. It must make zero real provider calls and incur zero provider cost.
- No paid canary or live cutover occurs until the provider-free completion
  package is independently accepted.

## Accepted Source Baseline

The executor must verify these bytes before copying any current untracked or
ignored source into the isolated worktree:

| Source | Bytes | SHA-256 |
|---|---:|---|
| Accepted design | 23,393 | `4b2a50076c4cd94910f8fd85e9c62c8222197d0846c3b0c8131228dea3266d73` |
| Active V1 `server.mjs` | 519,352 | `8440edd2edbce53b80dd1779f11efcfb5b5fc054068cba988d5026e3e18b4ecf` |
| Active V1 `scheduler-store.mjs` | 481,106 | `4433098e34116d841b57b0255f44a1285de7069b6afb05bd00eca13d3b76620f` |
| V1 real-pipe test | 22,408 | `047fc659c68d6f05725fb3742059cd20ae9ac387cc1e47139c5781f5fb00ef43` |
| V1 validation receipt | 3,453 | `6a44c28bfb5d6841b8031ac878fb186b3c72d4af108afabe44c9271596112290` |
| Current Chat launcher | 7,568 | `ad34bf80fc72a203a1138290cf9a88c5c23bb9839f349b9e42919134942b82e6` |
| Current thin/direct CLI source | 12,603 | `8a7e76f890dec09ba8ef109eaeee1bb288b7cf5d1596ee5843b86c0910c5301b` |
| Current Chat contract tests | 27,631 | `db74d578d818f0c733c19a5236461bfec7cc475f7bcbe3b6bac9d1ce821ca503` |
| Current runtime-isolation tests | 11,174 | `f1512a332ec62ff72a371a68650af004c45e112a7dc84f8dfd1c4b22b2192f80` |

If any baseline hash differs, stop before copying and reconcile the changed
owner/source. Do not overwrite the newer bytes or silently substitute an older
runtime.

## Current V1 Coverage and Gaps

Do not reimplement already proven behavior without a failing regression. V1
already demonstrates 50 logical readers, 10 writers, an active-origin ceiling,
same-origin exact single-flight, cross-origin status denial, settled durable
accounting, and a startup gate that yields to heartbeat timers.

The accepted spec is not yet fully implemented:

- `createProductionWorkerEnvelope()` hashes the authenticated origin into the
  contract identity, and `submitCandidateWorker()` hashes the origin-bearing
  payload. This prevents exact cross-origin requests from sharing one producer.
- V1 bypasses the schema-v5 single-writer table with
  `#parallelWriterAdmissions`, an in-memory map. Parallel writer ownership is
  therefore not durable across restart, and conflicts are not daemon-queued.
- `acquireProviderSlot()` hard-codes 50 DeepSeek read slots and 10 write slots.
  There is no independent, canary-derived total paid-provider window.
- `batch.submit` remains disabled while the CLI performs client-lifetime
  fanout. Dependency release and restart recovery are not daemon-authoritative.
- The visible real-pipe proof does not cover near-match non-coalescing,
  cross-origin result/cancel/subscription isolation, conflict queueing,
  accounting fault injection, ambiguous-dispatch restart, durable dependency
  release, or the full paid-canary policy.

## Scope Check

The work stays in one implementation plan because the origin, writer,
provider-window, dependency, accounting, and recovery changes share one schema
transition, one daemon protocol, one immutable runtime build, and one activation
gate. Releasing any slice independently would create competing runtime or store
truth. The tasks remain separately reviewable and testable, but deployment is
atomic at the final accepted V2 build.

## File Map

V2 is a successor package; never edit the V1 package in place.

- Create:
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SOURCE_BASELINE.json`
  — exact V1 source and installed-runtime hashes.
- Create:
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/build-candidate.ps1`
  — reproducibly copy the immutable V1 runtime to a disposable staging path,
  overlay V2 source, and compute the candidate build hash.
- Create:
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/verify-provider-free.ps1`
  — run focused tests and the complete real-pipe gate without credentials.
- Create/modify under
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/`:
  `server.mjs`, `orchestrator-daemon.mjs`,
  `lib/scheduler-store.mjs`, `lib/candidate-runtime.mjs`,
  `lib/execution-kernel.mjs`, `lib/daemon-protocol-v2.mjs`, and
  `lib/project-scheduler-policy.mjs`.
- Create under
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/`:
  `baseline.test.mjs`, `schema-v6-migration.test.mjs`,
  `origin-singleflight.test.mjs`, `writer-scope-queue.test.mjs`,
  `paid-provider-window.test.mjs`, `durable-batch.test.mjs`,
  `accounting-recovery.test.mjs`, `lease-recovery.test.mjs`,
  `provider-free-real-pipe.mjs`, and `provider-free-mock.mjs`.
- Modify: `.opencode/scripts/cheapluna-cli.mjs:1-358` — thin client only.
- Modify: `.opencode/tests/cheapluna-contract.test.mjs:1-838` — CLI,
  launcher, health, timeout, and route contracts.
- Modify only after accepted paid canary:
  `.opencode/scripts/cheapluna-chat-launcher.mjs:1-255` — pin exact V2 build
  and accepted paid window.
- Modify only after accepted paid canary:
  `.codex/tests/test_runtime_isolation.py:160-200` — assert the V2 pin and
  policy receipt.
- Create final package files:
  `MANIFEST.json`, `SHA256SUMS.txt`, `VALIDATION.json`,
  `CANARY_ACCEPTANCE.json`, and
  `DEEPLUNA_CHAT_PROJECT_SCHEDULER_20260817.md`.

---

### Task 1: Create the isolated V2 candidate and exact baseline gate

**Files:**

- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SOURCE_BASELINE.json`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/build-candidate.ps1`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/baseline.test.mjs`
- Seed: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/`

**Interfaces:**

- Consumes: installed immutable runtime build `5756cbc...e25` and the baseline
  table above.
- Produces: `build-candidate.ps1 -Destination <absolute-temp-path>` and a
  staged runtime whose source hash is deterministic before V2 edits.

- [ ] **Step 1: Create an isolated worktree from commit `c5ce38b`**

Use the `superpowers:using-git-worktrees` skill. Verify the destination is not
inside the dirty primary worktree and that the new branch starts at `c5ce38b`.

- [ ] **Step 2: Write the failing baseline test**

```javascript
test("V2 seed accepts only the exact active V1 runtime", () => {
  const baseline = JSON.parse(fs.readFileSync(baselinePath, "utf8"));
  assert.equal(baseline.source_runtime_build, ACTIVE_V1_BUILD);
  for (const expected of baseline.files) {
    assert.equal(sha256(path.join(sourceRuntime, expected.path)), expected.sha256);
  }
});
```

- [ ] **Step 3: Run the test and confirm the missing-baseline failure**

Run:

```powershell
node --test .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/baseline.test.mjs
```

Expected: FAIL because `SOURCE_BASELINE.json` and the V2 candidate do not yet
exist.

- [ ] **Step 4: Implement exact seeding and disposable build staging**

The build script must resolve and verify both source and destination, refuse an
existing nonempty destination, copy the full installed runtime to the
destination, then overlay only V2 candidate files:

```powershell
param([Parameter(Mandatory)][string]$Destination)
$source = Join-Path $env:LOCALAPPDATA "OpenCode\CheapLuna\runtime\5756cbcfa419c2db7b9529639e905767af6ca5d80ff1e723bde1c688d19f7e25"
$resolvedSource = (Resolve-Path -LiteralPath $source).Path
$resolvedDestination = [IO.Path]::GetFullPath($Destination)
if (-not (Test-Path -LiteralPath $resolvedSource -PathType Container)) { throw "V1 runtime missing" }
if (Test-Path -LiteralPath $resolvedDestination) { throw "Destination must not exist" }
New-Item -ItemType Directory -Path $resolvedDestination | Out-Null
Copy-Item -Path (Join-Path $resolvedSource "*") -Destination $resolvedDestination -Recurse
```

Use `Copy-Item` only for this bulk mechanical seed. Candidate source edits
after seeding use `apply_patch`.

After the full-runtime staging copy passes, copy these exact source files from
the verified V1 runtime into the V2 overlay directory: `server.mjs`,
`orchestrator-daemon.mjs`, `lib/scheduler-store.mjs`,
`lib/candidate-runtime.mjs`, `lib/execution-kernel.mjs`, and
`lib/daemon-protocol-v2.mjs`. Record each copied file's byte length and SHA-256
in `SOURCE_BASELINE.json`. The build script overlays these paths onto a fresh
staging copy; it never writes back to the installed V1 directory.

- [ ] **Step 5: Run the baseline test and source-hash replay**

Expected: PASS, with every listed V1 file and installed runtime source matching
its SHA-256.

- [ ] **Step 6: Commit the reviewable baseline files**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SOURCE_BASELINE.json `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/build-candidate.ps1 `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/baseline.test.mjs
git commit -m "test(deepluna): freeze V2 scheduler source baseline"
```

### Task 2: Add schema-v6 durable scheduler policy and migration

**Files:**

- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/daemon-protocol-v2.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/schema-v6-migration.test.mjs`

**Interfaces:**

- Produces: `CANDIDATE_STORE_SCHEMA_VERSION = 6`;
  `migrateCandidateSchedulerStoreV5ToV6({sourcePath,backupDirectory})`;
  `getCandidateProviderWindow({projectId})`;
  `configureCandidateProviderWindow({...})`; multi-row durable writer leases;
  scheduler telemetry records.
- Consumed by Tasks 4, 5, 6, 7, and 9.

- [ ] **Step 1: Write the migration failure tests**

Test all of these exact conditions:

```javascript
assert.equal(store.getCandidateStoreSchemaVersion(), 6);
assert.equal(store.database.pragma("quick_check", { simple: true }), "ok");
assert.deepEqual(store.database.pragma("foreign_key_check"), []);
assert.throws(
  () => migrateCandidateSchedulerStoreV5ToV6(activeStorePaths),
  /requires a quiescent store/i,
);
assert.equal(rollbackStore.getCandidateStoreSchemaVersion(), 5);
```

Also assert that a clean v5 copy migrates with zero active leases,
reservations, writer locks, provider transmissions, or batch producers.

- [ ] **Step 2: Run the focused test and confirm schema 5 fails**

```powershell
node --test .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/schema-v6-migration.test.mjs
```

Expected: FAIL because the candidate still reports schema 5 and lacks the V6
tables.

- [ ] **Step 3: Implement the schema-v6 tables and constraints**

Use strict tables with these keys:

```sql
CREATE TABLE writer_locks_v6 (
  project_id TEXT NOT NULL,
  fencing_token INTEGER NOT NULL,
  origin_id INTEGER NOT NULL,
  owner_job_id TEXT NOT NULL,
  owner_generation INTEGER NOT NULL,
  owner_lease_epoch INTEGER NOT NULL,
  canonical_worktree TEXT NOT NULL,
  worktree_identity TEXT NOT NULL,
  acquired_at_ms INTEGER NOT NULL,
  expires_at_ms INTEGER NOT NULL,
  PRIMARY KEY (project_id, fencing_token),
  UNIQUE (project_id, owner_job_id, owner_generation, owner_lease_epoch)
) STRICT;

CREATE TABLE project_provider_windows (
  project_id TEXT PRIMARY KEY,
  accepted_window INTEGER NOT NULL CHECK (accepted_window BETWEEN 1 AND 50),
  acceptance_receipt_sha256 TEXT NOT NULL,
  runtime_build_sha256 TEXT NOT NULL,
  configured_at_ms INTEGER NOT NULL
) STRICT;

CREATE TABLE scheduler_observations (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  job_id TEXT,
  observation_type TEXT NOT NULL,
  value_ms INTEGER NOT NULL,
  created_at_ms INTEGER NOT NULL
) STRICT;
```

The final `writer_locks` and `writer_lock_outputs` names replace the V5 tables
inside one migration transaction. V5 must be quiescent, backed up, and
fingerprinted before migration. Any failure restores the exact V5 backup and
leaves the source unchanged.

- [ ] **Step 4: Bump the daemon protocol profile to schema 6**

Change only the required store-schema constant and validation expectations:

```javascript
export const CANDIDATE_DAEMON_REQUIRED_STORE_SCHEMA_VERSION = 6;
```

- [ ] **Step 5: Run migration, rollback, integrity, and baseline tests**

Expected: all PASS; `quick_check=ok`, zero foreign-key violations, V5 rollback
hash exact.

- [ ] **Step 6: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/daemon-protocol-v2.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/schema-v6-migration.test.mjs
git commit -m "feat(deepluna): add durable scheduler schema v6"
```

### Task 3: Make exact single-flight cross-origin and keep subscribers isolated

**Files:**

- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/orchestrator-daemon.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/origin-singleflight.test.mjs`

**Interfaces:**

- Produces: one origin-independent producer fingerprint and one origin-bound
  public subscriber ID per origin/binding.
- Preserves: server-derived HMAC origin, cross-origin status/result/cancel
  denial, and detach-only cancellation while another subscriber remains.

- [ ] **Step 1: Write the cross-origin real-pipe test**

```javascript
const a = await connect(runtime, "origin-a");
const b = await connect(runtime, "origin-b");
const aSubmit = await a.request("worker.submit", exactRequest);
const bSubmit = await b.request("worker.submit", exactRequest);
assert.notEqual(aSubmit.job_id, bSubmit.job_id);
assert.equal(countWorkerBindings(db), 1);
assert.equal(mock.captureCount(), 1);
await assert.rejects(a.request("job.status", { jobId: bSubmit.job_id }), /NOT_FOUND_OR_NOT_OWNED/);
const detached = await a.request("job.cancel", { jobId: aSubmit.job_id });
assert.equal(detached.producer_cancelled, false);
assert.equal((await b.request("job.status", { jobId: bSubmit.job_id })).subscriber_state, "ATTACHED");
```

Submit one near-match request with one changed `definition_of_done` entry and
assert two bindings and two mock captures.

- [ ] **Step 2: Run the test and confirm cross-origin duplicate production**

Expected: FAIL because V1 includes origin hashes in the contract identity and
origin-bearing payload fingerprint.

- [ ] **Step 3: Split producer identity from subscriber identity**

In `createProductionWorkerEnvelope()` compute producer identity without origin:

```javascript
const producerIdentity = sha256(stableJson({ input, mode, projectId: session.projectId }));
const originContext = Object.freeze({
  originThreadHash: session.originThreadHash,
  originCapabilityHash: session.originCapabilityHash,
});
```

Keep `originContext` in the execution payload for the first producer’s private
artifact scope, but exclude it from `submitCandidateWorker()` producer
fingerprinting:

```javascript
const { originContext: _subscriberOrigin, ...producerPayload } = contract.payload;
const executionFingerprint = candidateSha256(canonicalPayloadJson({
  contractHash: contract.contractHash,
  inputFingerprint: contract.inputFingerprint,
  maximumAttempts,
  payload: producerPayload,
  poolId: contract.poolId,
  priority,
  projectId,
  role: contract.role,
}));
```

Never expose the first producer origin to another subscriber. Publish only the
validated public result packet through each origin-bound claim.

- [ ] **Step 4: Verify cancellation and terminal publication**

Run the cross-origin test twice: once canceling one subscriber before provider
completion and once after terminal publication. Both origins must retain only
their own public IDs and authorized packets.

- [ ] **Step 5: Run schema and real-pipe regression tests**

Expected: PASS with one producer for exact cross-origin requests, two producers
for the near match, and all denied cross-origin operations.

- [ ] **Step 6: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/orchestrator-daemon.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/origin-singleflight.test.mjs
git commit -m "feat(deepluna): isolate cross-origin single-flight subscribers"
```

### Task 4: Replace in-memory writers with durable conflict-aware queueing

**Files:**

- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/writer-scope-queue.test.mjs`

**Interfaces:**

- Produces:
  `tryLeaseCandidateGeneration({jobId,generation,workerId,leaseMs})` returning
  `{state:"LEASED", lease, writerAdmission}` or
  `{state:"DEFERRED", reason:"WRITER_SCOPE_CONFLICT"}`.
- Removes: `#parallelWriterAdmissions` and
  `#nextParallelWriterFencingToken`.

- [ ] **Step 1: Write the durable writer tests**

Exercise all exact cases:

```javascript
assert.equal(await submitWriter(worktreeA, ["a.txt"]), "RUNNING");
assert.equal(await submitWriter(worktreeB, ["b.txt"]), "RUNNING");
assert.equal(activeWriterRows(db), 2);
assert.equal((await submitWriter(worktreeA, ["a.txt"])).status, "QUEUED");
assert.equal(providerCapturesFor("conflicting-writer"), 0);
```

Also assert conflict for case-insensitive aliases, symlink aliases,
ancestor/descendant paths, and identical worktree identities. After the first
writer releases, the queued writer must run without resubmission.

- [ ] **Step 2: Run the test and confirm the in-memory/durable mismatch**

Expected: FAIL because V1 parallel admissions are in memory and conflicting
writers become failures instead of remaining queued.

- [ ] **Step 3: Implement atomic writer-aware leasing**

Inside one `BEGIN IMMEDIATE` transaction:

1. verify the generation is still `QUEUED`;
2. canonicalize `writerScope` and resolve filesystem identities;
3. remove expired writer rows whose owner lease is no longer current;
4. detect worktree, output, alias, and ancestor/descendant conflicts;
5. return `DEFERRED` without creating an attempt or consuming retry budget; or
6. create the lease and writer fence together and return `LEASED`.

Never create a provider reservation before `LEASED`.

- [ ] **Step 4: Prevent busy-looping while retaining durable queue truth**

In `candidate-runtime.mjs`, keep only a non-authoritative local suppression set:

```javascript
if (leaseResult.state === "DEFERRED") {
  this.#deferredWriters.add(schedulerJobId);
  return Object.freeze({ code: leaseResult.reason, status: "QUEUED" });
}
```

Clear the suppression set whenever any writer fence is released. SQLite
`generations.state='QUEUED'` remains the only recovery truth; restart may drop
the optimization without losing work.

- [ ] **Step 5: Verify restart behavior**

Stop the test daemon while two non-conflicting writer rows exist. Restart
against the copied store and assert that stale/ambiguous writers are fenced or
quarantined and that no undeclared write or provider retry occurs. A merely
queued conflicting writer remains queued.

- [ ] **Step 6: Run focused, schema, single-flight, and real-pipe tests**

Expected: PASS; up to ten non-conflicting writers, deterministic queueing for
conflicts, durable fences, and zero conflict-triggered provider calls.

- [ ] **Step 7: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/writer-scope-queue.test.mjs
git commit -m "feat(deepluna): queue durable non-overlapping writers"
```

### Task 5: Introduce the independent canary-derived paid-provider window

**Files:**

- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/project-scheduler-policy.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/daemon-protocol-v2.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/paid-provider-window.test.mjs`

**Interfaces:**

- Produces:
  `normalizePaidProviderPolicy({projectId,acceptedWindow,acceptanceReceiptSha256,runtimeBuildSha256})`;
  `acquirePaidProviderLease({storeRoot,projectId,policy,signal})`; health fields
  `paid_provider_window`, `paid_provider_active`, and
  `paid_provider_acceptance_sha256`.
- Default production window: `1`.

- [ ] **Step 1: Write the paid-window failure test**

```javascript
const policy = normalizePaidProviderPolicy({
  projectId,
  acceptedWindow: 2,
  acceptanceReceiptSha256: "a".repeat(64),
  runtimeBuildSha256: "b".repeat(64),
});
await submitFiveDelayedReads();
assert.equal(mock.maximumActiveRequests(), 2);
assert.equal(health.capacity.read_limit, 50);
assert.equal(health.capacity.write_limit, 10);
assert.equal(health.capacity.paid_provider_window, 2);
```

Assert missing, malformed, runtime-mismatched, or unaccepted policy blocks all
provider dispatches while leaving local health inspectable.

- [ ] **Step 2: Run the test and confirm V1 reaches above the policy window**

Expected: FAIL because `acquireProviderSlot()` hard-codes 50 reads/10 writes.

- [ ] **Step 3: Implement immutable policy normalization**

```javascript
export const DEFAULT_PAID_PROVIDER_WINDOW = 1;

export function normalizePaidProviderPolicy(raw) {
  if (raw.acceptedWindow < 1 || raw.acceptedWindow > 50) {
    throw policyError("PAID_WINDOW_UNACCEPTED");
  }
  requireSha256(raw.acceptanceReceiptSha256);
  requireSha256(raw.runtimeBuildSha256);
  return Object.freeze({ ...raw });
}
```

Persist the exact policy in `project_provider_windows`. A runtime hash or
receipt mismatch makes readiness `BLOCKED` for provider work.

- [ ] **Step 4: Gate paid jobs separately from logical lanes**

Acquire one total DeepSeek paid lease before constructing the provider manager;
release it only after the job’s final provider call is reconciled or held
unknown. Reads and writes share the same paid window. Logical read/write leases
remain 50/10 and are reported separately.

Provider-window saturation queues work; it must not create a failure packet,
retry, fallback, or reservation.

- [ ] **Step 5: Expose and validate health fields**

Add exact public fields to the protocol validator and CLI health projection.
Do not expose receipt contents or origin data—only the accepted SHA-256 and
counts.

- [ ] **Step 6: Run focused and related suites**

Expected: policy 1/2/5 bounds maximum active fake-provider work exactly, while
50 logical readers and 10 logical writers remain admissible.

- [ ] **Step 7: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/project-scheduler-policy.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/daemon-protocol-v2.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/paid-provider-window.test.mjs
git commit -m "feat(deepluna): gate paid provider concurrency by accepted canary"
```

### Task 6: Move dependency scheduling into the durable daemon

**Files:**

- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/orchestrator-daemon.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/durable-batch.test.mjs`

**Interfaces:**

- Produces: `submitCandidateBatch({originId,projectId,batch})`,
  `listReadyCandidateBatchNodes({projectId,limit})`, and a daemon batch pump.
- Replaces: disabled `batchSubmit: () => false` and client-lifetime dependency
  release.

- [ ] **Step 1: Write the durable DAG failure tests**

Use `A -> {B,C} -> D` with accepted evidence verdicts:

```javascript
const submitted = await client.request("batch.submit", { input: dag });
assert.equal(providerCapturesFor("B"), 0);
await completeNode("A", "PASS");
assert.deepEqual(new Set(startedNodes()), new Set(["B", "C"]));
await restartDaemon();
assert.equal((await client.request("batch.status", { batchId: submitted.batch_id })).status, "RUNNING");
```

Also assert a failed parent durably blocks descendants and restart never
releases a dependency twice.

- [ ] **Step 2: Run the test and confirm batch submission is rejected**

Expected: FAIL with the current disabled batch validator/handler.

- [ ] **Step 3: Implement strict canonical batch admission**

Validate 1–50 nodes, unique node IDs, acyclic edges, explicit concurrency,
read-only mode for automatic fanout, exact task contracts, and accepted parent
verdicts. Persist `batch_runs`, claims, nodes, edges, dependency states, and
worker bindings in one transaction.

- [ ] **Step 4: Implement daemon-owned node release**

Only the daemon batch pump may transition a node from `WAITING` to `READY`.
After every accepted worker terminal, update dependency rows and enqueue newly
ready nodes in the same durable transaction. Client disconnect affects only its
subscription, not the batch producer.

- [ ] **Step 5: Recover after restart**

On startup, reconcile terminal worker bindings, mark ambiguous externally
started nodes held, and resume only nodes that are provably `READY` with no
active/unknown transmission. Never create a replacement transmission for an
ambiguous node.

- [ ] **Step 6: Run focused and cross-feature tests**

Expected: DAG order is exact across restart, duplicate batch submissions
coalesce, and origin isolation matches worker claims.

- [ ] **Step 7: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/orchestrator-daemon.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/durable-batch.test.mjs
git commit -m "feat(deepluna): make batch dependencies daemon durable"
```

### Task 7: Prove accounting faults, lease timing, and ambiguous recovery

**Files:**

- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/execution-kernel.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs`
- Modify: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/accounting-recovery.test.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/lease-recovery.test.mjs`

**Interfaces:**

- Produces health telemetry:
  `lease_heartbeat_max_lateness_ms`, `sqlite_max_wait_ms`,
  `event_loop_max_lag_ms`, `active_transmissions`, and
  `unknown_transmissions`.
- Preserves: reservation-before-dispatch, exactly-once reconciliation, and
  no-retry ambiguity.

- [ ] **Step 1: Write accounting fault-injection tests**

Inject failures at each boundary:

```javascript
await failAfterReservationBeforeDispatch();
assert.equal(transmissionState(db), "RELEASED");
await failAfterDispatchBeforeResponse();
assert.equal(transmissionState(db), "UNKNOWN");
await assert.rejects(submitAnotherProviderJob(), /ACCOUNTING_UNCERTAIN/);
assert.deepEqual(replayProjectTotals(db), health.budget);
```

Call reconciliation twice with the same provider request identity and assert
the second call is idempotent, not a second cost entry.

- [ ] **Step 2: Write deterministic lease and restart tests**

Use the delayed fake provider and synchronous startup pressure. Assert the
bounded four-wide start gate permits heartbeat progress and records finite
lateness. Kill the daemon after fake dispatch but before response, restart, and
assert the attempt becomes `UNKNOWN` with no second mock capture.

- [ ] **Step 3: Run tests and confirm missing telemetry/recovery assertions fail**

Expected: existing accounting characterization may pass, but tests must fail on
the absent telemetry and any ambiguous-restart retry path.

- [ ] **Step 4: Record bounded timing observations**

Measure event-loop lag around manager construction, SQLite transaction wait,
and heartbeat lateness. Store only numeric timing and identifiers—never secrets
or task content. Health reports project maxima for the current daemon boot.

- [ ] **Step 5: Harden unknown-state recovery**

Any dispatched transmission without exact terminal reconciliation is marked
`UNKNOWN`. The project provider gate closes until a deterministic reconciliation
receipt exists. Restart never converts `UNKNOWN` to queued and never calls the
provider for it.

- [ ] **Step 6: Run focused tests under 1, 2, 5, 10, and 50 logical clients**

All runs use the fake provider. Expected: zero stale attempts, zero duplicate
captures, exactly replayable accounting, and no unknown state except the
deliberate ambiguity case.

- [ ] **Step 7: Commit**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/execution-kernel.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/candidate-runtime.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/lib/scheduler-store.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/candidate/runtime/server.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/accounting-recovery.test.mjs `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/lease-recovery.test.mjs
git commit -m "test(deepluna): prove accounting and ambiguous recovery"
```

### Task 8: Reduce the CLI to a thin daemon client

**Files:**

- Modify: `.opencode/scripts/cheapluna-cli.mjs:1-358`
- Modify: `.opencode/tests/cheapluna-contract.test.mjs:1-838`

**Interfaces:**

- Produces: one `batch.submit` RPC; bounded `status`/`batch-status`/`cancel`;
  stable-ID reattachment; no client-owned dependency or accounting state.
- Removes: whole-wave direct `Promise.all` submission and local dependency
  release as scheduling authority.

- [ ] **Step 1: Add failing CLI contract tests**

Stub the daemon client and assert:

```javascript
await runCli(["batch-submit", batchPath]);
assert.deepEqual(recordedMethods, ["batch.submit"]);
await runCli(["status", stableJobId]);
assert.deepEqual(recordedMethods.at(-1), "job.status");
```

Simulate a client poll timeout and assert the CLI prints
`AMBIGUOUS_CLIENT_TIMEOUT` with the stable job ID and performs zero submit
retries.

- [ ] **Step 2: Run the CLI tests and confirm multiple worker submissions fail**

Expected: FAIL because V1 `batch-submit` directly fans out `worker.submit`.

- [ ] **Step 3: Delete client scheduling authority**

Keep local JSON parsing only for user-facing early validation. Submit the
canonical batch once, poll daemon status if requested, and reattach by the
returned stable ID. The CLI must not calculate cost from health deltas,
checkpoint dependencies, or retry a timed-out submit.

- [ ] **Step 4: Add health projection for separate capacity planes**

Print logical reads/writes, paid-provider window/active count, queue size,
reservations, unknown transmissions, runtime build, and policy receipt SHA.

- [ ] **Step 5: Run Node and Python host contract tests**

```powershell
node --test .opencode/tests/cheapluna-contract.test.mjs
python -m pytest .codex/tests/test_runtime_isolation.py -q
```

Expected: all pass without starting a provider call.

- [ ] **Step 6: Commit**

```powershell
git add .opencode/scripts/cheapluna-cli.mjs .opencode/tests/cheapluna-contract.test.mjs
git commit -m "refactor(deepluna): make CLI a thin durable-scheduler client"
```

### Task 9: Complete the provider-free real-pipe gate

**Files:**

- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/provider-free-mock.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/test/provider-free-real-pipe.mjs`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/verify-provider-free.ps1`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/MANIFEST.json`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SHA256SUMS.txt`
- Create: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/VALIDATION.json`

**Interfaces:**

- Produces one immutable provider-free completion package and candidate build
  hash eligible for separate canary review.

- [ ] **Step 1: Expand the real-pipe test to all 18 specification checks**

The test must assert, not merely report:

1. exact build and route pin;
2. authenticated multi-origin transport;
3. 50 readers;
4. 10 non-conflicting writers;
5. conflicting writers queue;
6. exact cross-origin single-flight;
7. near matches do not coalesce;
8. cross-origin status/result/cancel/subscription denial;
9. per-transmission reservation and exactly-once reconciliation;
10. accounting fault injection;
11. deterministic lease timing;
12. disconnect/reattach;
13. daemon restart recovery;
14. ambiguous dispatch no-retry;
15. daemon-owned dependency ordering;
16. clean shutdown;
17. `quick_check=ok` and zero foreign-key violations; and
18. zero leases, reservations, unknowns, writer locks, or active work after
    quiescence.

- [ ] **Step 2: Prove the old V1 package does not satisfy the expanded gate**

Run the new test against V1 staging. Expected: FAIL on cross-origin coalescing,
durable writers, paid-window policy, and daemon batch scheduling.

- [ ] **Step 3: Run the expanded gate against V2**

```powershell
powershell -NoProfile -File .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/verify-provider-free.ps1
```

Expected: PASS with the fake provider endpoint only. The script must fail if a
real provider hostname, credential, token, cost, or nonzero external-call
counter appears.

- [ ] **Step 4: Build the immutable candidate and ledger**

The manifest records source-basis hashes, overlay hashes, runtime file count,
total bytes, runtime build hash, test commands, exact project, route, schema 6,
logical limits, paid window 1, and zero-provider gate receipt. Generate
`SHA256SUMS.txt` from final bytes after all reports are sealed.

- [ ] **Step 5: Replay the package independently**

Recompute every hash, rerun syntax and tests from a fresh disposable staging
directory, and verify no package path escapes the package root. `VALIDATION.json`
must say `ELIGIBLE_FOR_CANARY_REVIEW`, not activated or released.

- [ ] **Step 6: Commit the reviewable V2 package**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2
git commit -m "feat(deepluna): seal provider-free V2 scheduler candidate"
```

### Task 10: Stop for separate paid-canary acceptance

**Files:**

- Create after authorization:
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/CANARY_ACCEPTANCE.json`
- Create after authorization:
  `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/DEEPLUNA_CHAT_PROJECT_SCHEDULER_20260817.md`

**Interfaces:**

- Consumes: independently accepted Task 9 package and exact candidate hash.
- Produces: accepted paid-provider window and cumulative canary ledger.

- [ ] **Step 1: Present the provider-free package to Sol and stop**

Do not transmit a canary until Sol explicitly accepts the exact manifest,
runtime hash, provider-free receipt, and maximum cost.

- [ ] **Step 2: After acceptance, run the single-transmission canary**

Use one bounded, non-sensitive, read-only exact task, one attempt,
`DIRECT_PRO`, `NO_LUNA`, and an explicit cost ceiling. Verify route, runtime,
origin, single-flight, transmission count, cost, and settled postflight ledger.

- [ ] **Step 3: Record the canary ladder without automatic escalation**

The allowed ladder is `1 -> 2 -> 5 -> 10 -> 15 -> 20 -> 30 -> 40 -> 50`.
Each increase requires separate Sol acceptance and at least two consecutive
clean waves. Stop on any stale lease, duplicate transmission, unknown
accounting, origin leak, timeout ambiguity, writer conflict, route drift, cost
mismatch, or fallback.

- [ ] **Step 4: Seal the accepted window**

`CANARY_ACCEPTANCE.json` records every wave, task hash, runtime hash,
transmission IDs, actual cumulative cost, postflight zeros, and the highest
accepted clean stage. It must not infer acceptance from capacity or a worker
packet.

- [ ] **Step 5: Commit the accepted canary receipt**

```powershell
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/CANARY_ACCEPTANCE.json `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/DEEPLUNA_CHAT_PROJECT_SCHEDULER_20260817.md
git commit -m "docs(deepluna): record accepted scheduler canary window"
```

### Task 11: Pin, activate, verify, and retain rollback

**Files:**

- Modify: `.opencode/scripts/cheapluna-chat-launcher.mjs:7-22,150-160`
- Modify: `.opencode/tests/cheapluna-contract.test.mjs:800-838`
- Modify: `.codex/tests/test_runtime_isolation.py:160-200`
- Update: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/VALIDATION.json`
- Update: `.opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SHA256SUMS.txt`

**Interfaces:**

- Consumes: exact accepted runtime build and `CANARY_ACCEPTANCE.json` SHA-256.
- Produces: launcher pin, accepted paid window, live READY health, and rollback
  receipt pointing to V1.

- [ ] **Step 1: Write the failing launcher-pin tests**

```javascript
assert.equal(CHEAPLUNA_BUILD, accepted.runtime_build_sha256);
assert.equal(CHEAPLUNA_PAID_PROVIDER_WINDOW, accepted.accepted_window);
assert.equal(CHEAPLUNA_CANARY_ACCEPTANCE_SHA256, accepted.file_sha256);
```

Python isolation tests must assert the same literal build and receipt hashes.

- [ ] **Step 2: Run tests and confirm the launcher still pins V1**

Expected: FAIL with the old `5756cbc...e25` pin.

- [ ] **Step 3: Patch only the exact launcher and test bytes**

Before editing, verify their hashes still match the accepted source baseline or
the explicitly reconciled successor. If they drift, stop. Pin the exact V2
build, accepted window, and acceptance receipt hash; do not edit unrelated
dirty files.

- [ ] **Step 4: Run all host and candidate tests before recycle**

```powershell
node --test .opencode/tests/cheapluna-contract.test.mjs
python -m pytest .codex/tests/test_runtime_isolation.py -q
powershell -NoProfile -File .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/scripts/verify-provider-free.ps1
```

- [ ] **Step 5: Verify preflight quiescence**

Require exact V1 daemon identity, `quick_check=ok`, zero foreign-key
violations, zero active/queued work, zero leases, zero writer locks, zero
in-flight/unknown transmissions, and zero open/unknown reservations. Archive
the preflight receipt without changing scheduler rows.

- [ ] **Step 6: Recycle only the exact project daemon**

Stop the sole V1 project daemon, start the exact V2 build through the protected
launcher, and reject any foreign or duplicate daemon owner. Do not stop other
projects or restore the working tree.

- [ ] **Step 7: Verify live postflight**

Health must show exact project, V2 build, schema 6, 50/10 logical lanes, the
accepted paid-provider window, matching acceptance SHA, settled accounting,
zero queue, and `DIRECT_PRO / NO_LUNA`. Run one provider-free authenticated
pipe probe; do not run an extra paid job merely to test activation.

- [ ] **Step 8: Seal activation and rollback evidence**

Update `VALIDATION.json` only after live postflight passes. Preserve the V1
runtime, its launcher pin, and its exact build hash as the rollback target.
Rollback stops new provider dispatch first and never erases transmission
history.

- [ ] **Step 9: Commit the exact host pin and final receipts**

```powershell
git add .opencode/scripts/cheapluna-chat-launcher.mjs `
  .opencode/tests/cheapluna-contract.test.mjs `
  .codex/tests/test_runtime_isolation.py
git add -f .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/VALIDATION.json `
  .opencode/upgrades/CL-CHAT-PROJECT-SCHEDULER-20260817-V2/SHA256SUMS.txt
git commit -m "feat(deepluna): activate accepted V2 project scheduler"
```

## Final Acceptance Checklist

- [ ] Exactly one daemon and one SQLite ledger own scheduling truth.
- [ ] The CLI has no competing queue, dependency, lease, retry, or cost truth.
- [ ] Exact cross-origin duplicates share one producer and retain isolated
  subscriber IDs and permissions.
- [ ] Near matches do not coalesce.
- [ ] Ten non-conflicting writers are durable; conflicts queue without provider
  calls or retry consumption.
- [ ] Paid-provider concurrency is independent and equals no more than the
  highest accepted canary stage.
- [ ] Every transmission reserves before dispatch and reconciles exactly once.
- [ ] Unknown transmission state blocks further provider calls and never
  auto-retries after restart.
- [ ] Lease timing, SQLite wait, and event-loop lag are observable without
  secrets.
- [ ] Dependency release is daemon-durable across client disconnect and daemon
  restart.
- [ ] The provider-free real-pipe gate covers all 18 checks with zero real
  provider traffic and zero cost.
- [ ] The canary ladder is separately accepted and stops on the first anomaly.
- [ ] The launcher pins only the exact accepted V2 build and policy receipt.
- [ ] V1 remains byte-identical and available for rollback.
- [ ] No scientific, physical, package, release, destructive, credential, or
  final-authority boundary changed.
