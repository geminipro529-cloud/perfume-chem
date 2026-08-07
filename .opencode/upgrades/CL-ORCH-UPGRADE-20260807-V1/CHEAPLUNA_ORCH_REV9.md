# CHEAPLUNA ORCHESTRATION BEHAVIOR UPGRADE — CL-ORCH-UPGRADE-20260807-V1

## 0.0 Revision metadata

revision_id: REV-9
plannotator_review_id: PR-20260807-CL-ORCH-V1-R9
revision_kind: INTEGRITY-PACKAGING CORRECTION (no architecture redesign)
primary_execution_authority: EXTERNAL_SHA256_RECEIPT
authority_file: CHEAPLUNA_ORCH_REV9.md
receipt_file: CHEAPLUNA_ORCH_REV9.sha256
authority_rule: SHA256(exact_saved_CHEAPLUNA_ORCH_REV9.md_bytes) == external_receipt_sha256; the receipt is immutable once review begins.
self_hash_note: This document does NOT hash itself as its primary authority. In-document canonical body/whole-file hashes are absent by design; integrity is carried by the external receipt.
governing_chain: REV-8 (superseded by REV-9 integrity packaging) -> REV-7 -> REV-6 -> REV-5 -> REV-3; REV-4 declared NON_EXECUTABLE_HASH_MISMATCH.

---

## 0. Intent

Upgrade the CheapLuna delegation layer (direct DeepSeek provider lock, V4 tool-call
compatibility, three V4-Flash semantic routes, local-first deterministic routing, 4+1
concurrency, DAG micro-waves, unique invocation IDs, cache-reuse prompt ordering, local
semantic result cache, packet minimization, structured outputs, bounded retries, circuit
breakers, single-writer, canaries, old-vs-new benchmark) while preserving exact source
fidelity, single-writer behavior, deterministic validation, abstention, provenance, and the
existing canonical-IO quarantine.

REV-3, REV-5, REV-6, REV-7, and REV-8 were approved as exact integrated execution contracts.
REV-8 was declared `REV8_EXECUTION_CONTRACT_VERIFICATION: FAIL` because its in-document canonical
integrity metadata did not reproduce from the exact stored file. REV-9 is an integrity-packaging
correction only: it carries REV-8's accepted semantic architecture and execution guards unchanged
and replaces the fragile in-document self-hash authority with an external SHA-256 receipt over the
exact saved file bytes. The four-layer authority verification (REV-3, REV-5, REV-6, REV-7) and the
REV-9 external-receipt verification result are recorded in
`CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json`.

**PCV3 FREEZE is respected throughout.** No PCV3 source, test, run, inventory, formula, or
planning artifact is touched. `PCV3_WAVE_2` stays `NOT_STARTED`.

## 0.1 Execution authorization (binding)

- Ancestor governing plan REV-3 (verified): canonical body 24305 bytes / SHA-256
  `57a914d0c1bb10c180cee83afe8fffd6f4bb1517bcd60b5d7a81b69be1f8a459`; canonical whole-file
  25287 bytes / SHA-256 `9c8d3ac7c7419ab17d0997e1d932510c6e3a9829023d4471c7b23fb2d12d37b8`.
- Approved execution contract REV-5 (verified): canonical body 31518 bytes / SHA-256
  `7c04da3bd0c6dbe2ed6de93a75bdcfc22b1650ca5909b9b8b6cab2e6ae0d18c2`; canonical whole-file
  32311 bytes / SHA-256 `498afa5417d10a046c42a42694e91f8d242c7665102e5e40c8ad209cdf295c73`.
- Approved execution contract REV-6 (verified): canonical body 36485 bytes / SHA-256
  `24497ebcf2a1fec38ba83f0700f620ef8fbe442f20f004095fc14f70251e9e1c`; canonical whole-file
  37492 bytes / SHA-256 `f0ba18b73144ca3dc2efe1a2ec6b9d6334f0eed6419daf0410eaa5235d2797a8`.
- Approved execution contract REV-7 (verified): canonical body 39740 bytes / SHA-256
  `49bb3b269702331b006fa3657b9d4c633e46b099c86c3827672f13a6885a93b3`; canonical whole-file
  40956 bytes / SHA-256 `f40e6a1133f5b4a164fafdd306658230825dc3bdef175cb8274fec2f853ad8e6`.
- REV-8 carried the architecture forward but was declared `REV8_EXECUTION_CONTRACT_VERIFICATION:
  FAIL` on in-document hash reproduction; it is superseded by REV-9's integrity packaging.
- Authority gates for this upgrade: `REV3_AUTHORITY_VERIFICATION: PASS`,
  `REV5_EXECUTION_CONTRACT_VERIFICATION: PASS`, `REV6_EXECUTION_CONTRACT_VERIFICATION: PASS`, and
  `REV7_EXECUTION_CONTRACT_VERIFICATION: PASS` are required before any implementation write; all
  four identities are recorded in the authorization artifact. Otherwise -> `PLAN_AUTHORITY_HOLD`;
  stop before implementation.
- Primary execution authority for REV-9: `SHA256(exact_saved_CHEAPLUNA_ORCH_REV9.md_bytes) ==
  external_receipt_sha256`, where `external_receipt_sha256` is recorded in
  `CHEAPLUNA_ORCH_REV9.sha256` and verified by a second independent process
  (`EXTERNAL_SHA256_RECEIPT_VERIFICATION: PASS`). The receipt is immutable once review begins.
- This document does not require the Markdown to hash itself as its primary authority.

## 1. Resolved baseline (exploration complete, verified on disk)

| Item | Resolved value |
|------|----------------|
| Logical project | `perfume-chem-cheapluna-isolated` |
| State root (active) | `D:\chatbots\perfume-chem\.opencode\.deepluna-home` (gitignored; bridge sets `DEEPSEEK_ORCHESTRATOR_HOME` here) |
| Project home | `...\.opencode\.deepluna-home\projects\perfume-chem-cheapluna-isolated` (jobs/, cache/results/, daemon-v2/scheduler.sqlite3, worker-state-v5.json, locks/, batches/, negative-admission-v1/) |
| Secondary home | `D:\chatbots\perfume-chem\.cheapluna-home` (untracked, legacy — recorded only, never used) |
| Runtime root | `%LOCALAPPDATA%\OpenCode\CheapLuna\runtime\b98f913fe8e87a17d697a86f0fe035eabef9517642dee1fe3f33651f76fdb44f` (build hash self-computed from `CANDIDATE_RUNTIME_MANIFEST_FILES`, 20 files, verified in daemon handshake) |
| Scheduler entry | `server.mjs` (MCP server + exports daemon connect); daemon = `node server.mjs --daemon --project-id=perfume-chem-cheapluna-isolated` |
| Worker launcher | `local-executor.mjs`; execution kernel `lib/execution-kernel.mjs` |
| DeepSeek adapter | `server.mjs` request builder (~L2475); provider pool `lib/provider-pools.mjs` |
| Queue / retry / cache / provenance / packet | `lib/scheduler-store.mjs` (469 KB), `lib/result-protocol.mjs`, `lib/evidence-protocol.mjs`, `lib/transmission-budget-controller.mjs`, `lib/batch-dag.mjs`, `lib/identity.mjs` |
| Capacity | `lib/capacity-policy.mjs`; bridge env reader lanes = 5 today |
| Daemon state | running (PID 31932), sqlite mtime 2026-08-07 00:13; profile `cheapluna-chat` `BLOCKED` (STOP_FOR_SOL) |
| Provider today | DeepInfra (bridge requires `PERFUME_CHEAPLUNA_DEEPINFRA_API_TOKEN`; **not set**). Historical only — no new DeepInfra calls this upgrade. |
| Direct DeepSeek | direct profile exists in runtime (`https://api.deepseek.com/chat/completions`, model `deepseek-v4-flash`); `PERFUME_DEEPSEEK_API_KEY` is set (user+process) |
| Host drivers | `.opencode/scripts/cheapluna-bridge.ps1`, `cheapluna-cli.mjs`, `cheapluna-drain.mjs`, `delegation_pure.mjs` |
| Plugins | `.opencode/plugins/cheapluna-cache-first.js`, `cheapluna-budget-guard.js`, `daemon-health-guard.js` (health guard references the wrong sqlite store — fix to active isolated daemon) |
| Config | `opencode.json` (tracked): MCP `cheapluna` registered; `cheapluna`/`cheapluna-write` command templates updated to the V4-Flash route set |

Branch/HEAD of the perfume-chem repo: `codex/add-inventory-materials` @ `7839317`. The
isolated project is not a git repo; its identity is the runtime build hash.

## 2. Modification surface (allowlist) — everything else is read-only

1. Runtime tree under `%LOCALAPPDATA%\OpenCode\CheapLuna\runtime\` — **new immutable build dir only**.
2. `.opencode/scripts/cheapluna-bridge.ps1`, `cheapluna-cli.mjs`, `cheapluna-drain.mjs`, `delegation_pure.mjs`.
3. `.opencode/plugins/cheapluna-*.js` (cache-first, budget-guard, daemon-health-guard).
4. `opencode.json` — only the `cheapluna`/`cheapluna-write` command templates and MCP env (minimal, tracked).
5. New upgrade directory (below).

**Zero writes** to `engine/`, `tests/`, `backend/`, `data/`, `formulas/`, `runs/`, `docs/`,
`inventory.txt`, or any PCV3 artifact.

## 3. Upgrade directory, immutable snapshot, provenance guard, immutable runtime install

- Upgrade dir: `.opencode/upgrades/CL-ORCH-UPGRADE-20260807-V1/` (inside repo, outside `runs/`
  -> outside PCV3 run artifacts; auditable, persistent).
- `pre_change/` holds byte-for-byte copies of every file that may be modified.
- `CHEAPLUNA_PRECHANGE_STATE.json` = resolution table + `CHEAPLUNA_PRECONDITION_SHA256SUMS.json`
  (exact SHA-256 of every modifiable file, incl. the 20-file runtime manifest; non-self-referential).
- **Target-path provenance guard.** Before modifying every existing repository allowlist file,
  record `git status --short -- <path>`, `git diff -- <path>`, and SHA-256. Classify each as
  CLEAN_EXPECTED_BASE / PRE_EXISTING_USER_CHANGE / PRE_EXISTING_AUTHORIZED_CHANGE /
  UNTRACKED_PRE_EXISTING / AUTHORITY_UNRESOLVED. If upgrade changes cannot be cleanly separated
  from pre-existing bytes -> `TARGET_PATH_PROVENANCE_HOLD` (do not overwrite, reset, restore,
  stash, or normalize unrelated work). Applies to `.opencode/scripts/cheapluna-bridge.ps1`,
  `cheapluna-cli.mjs`, `cheapluna-drain.mjs`, `delegation_pure.mjs`,
  `.opencode/plugins/cheapluna-cache-first.js`, `cheapluna-budget-guard.js`,
  `daemon-health-guard.js`, and `opencode.json`.
- **Immutable runtime install only (no patch-in-place).** Old runtime = READ_ONLY / IMMUTABLE.
  Candidate construction happens in a working copy only. After ALL patches are complete:
  recompute the manifest; compute the candidate runtime identity; install a new immutable
  runtime directory named by the verified identity; validate all candidate bytes; only then
  allow bridge cutover. If a new immutable build cannot be installed:
  `RUNTIME_BUILD_INSTALL_HOLD` — stop, never patch the baseline runtime.

## 4. Provider lock — DEEPSEEK DIRECT ONLY, V4 FLASH ONLY

- `CHEAPLUNA_PROVIDER_CONFIG.json`: `provider=deepseek`, `base_url=https://api.deepseek.com`,
  `api_model=deepseek-v4-flash`, `internal_display_label=DS-V4-FLASH-3107` (display/provenance
  metadata only), `snapshot_claim=false`.
- Allowed model routes (exhaustive):
  - `LOCAL` — `provider_call=false`.
  - `FLASH_FAST` — provider deepseek, model deepseek-v4-flash, thinking disabled.
  - `FLASH_HIGH` — provider deepseek, model deepseek-v4-flash, thinking enabled, reasoning_effort high.
  - `FLASH_MAX` — provider deepseek, model deepseek-v4-flash, thinking enabled, reasoning_effort max.
- **Removed:** DIRECT_PRO, V4_PRO, deepseek-v4-pro, and any Pro-escalation route. No worker may
  escalate to DeepSeek V4 Pro. DeepInfra/Nemotron/GLM/Sol routes are excluded from this profile.
- Fallback disabled (`NO_LUNA`); no provider switch after any failure. DeepInfra calls during
  this upgrade: **0**; V4-Pro calls during this upgrade: **0**.
- If direct DeepSeek is unavailable at probe: `DEEPSEEK_DIRECT_PROVIDER_HOLD` — stop affected
  model work, keep local deterministic operations.

### 4.1 Credential safety

- Bridge maps the existing private env credential to the DeepSeek client internally.
- Never print the API key; never write it into JSON, opencode.json, logs, benchmark artifacts,
  or hashes intended for reports.
- Artifacts record only `credential_source_name` and `credential_present: true|false`.
  Credential values are never persisted.

## 5. Phase P0 — Freeze guard + four-layer authority verification + immutable snapshots

1. Assert PCV3 freeze (no writes outside the section 2 allowlist; log a marker).
2. Verify ancestor governing plan REV-3 under its declared convention. Mismatch ->
   `PLAN_AUTHORITY_HOLD`; stop. Record `REV3_AUTHORITY_VERIFICATION: PASS`.
3. Independently verify REV-5 under its declared convention. Mismatch -> `PLAN_AUTHORITY_HOLD`;
   stop. Record `REV5_EXECUTION_CONTRACT_VERIFICATION: PASS`.
4. Independently verify REV-6 under its declared convention. Mismatch -> `PLAN_AUTHORITY_HOLD`;
   stop. Record `REV6_EXECUTION_CONTRACT_VERIFICATION: PASS`.
5. Independently verify REV-7 under its declared convention. Mismatch -> `PLAN_AUTHORITY_HOLD`;
   stop. Record `REV7_EXECUTION_CONTRACT_VERIFICATION: PASS`.
6. Verify the REV-9 external receipt: a second independent process reads the exact saved
   `CHEAPLUNA_ORCH_REV9.md` file and confirms `SHA256(file_bytes) == external_receipt_sha256`.
   Require `EXTERNAL_SHA256_RECEIPT_VERIFICATION: PASS`. Mismatch -> `PLAN_AUTHORITY_HOLD`; stop.
   Record exact_file_byte_size separately.
7. Resolve section 1 into `CHEAPLUNA_PRECHANGE_STATE.json` (live daemon PID, sqlite mtime, build hash).
8. Build immutable `CHEAPLUNA_PRECONDITION_SHA256SUMS.json` (non-self-referential).
9. Copy all modifiable files into `pre_change/` (byte-for-byte).
10. Run the target-path provenance guard (section 3) and record classifications.
11. `CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json` (records REV-3, REV-5, REV-6, REV-7
    identities, the REV-9 external receipt and its verification, PCV3 freeze, allowlist,
    credential_source_name / credential_present only).

## 6. Phase P1A — Direct DeepSeek capability probe (OLD immutable runtime, current scheduler)

Bounded harmless probes A-D against `api.deepseek.com` via the OLD immutable runtime's existing
direct-DeepSeek route, using EPHEMERAL invocation/environment configuration only. Do NOT edit the
live bridge, plugins, opencode.json, scheduler implementation, or runtime merely to obtain the
probe. With the CURRENT scheduler untouched: A thinking disabled; B thinking enabled / effort
high; C thinking enabled / effort max; D thinking + one harmless tool-call loop. Record
requested vs returned model, system_fingerprint (if exposed), HTTP status, first-token + total
latency, thinking state, reasoning effort, tool-call behavior, JSON validity,
prompt_cache_hit/miss_tokens, input/output/reasoning tokens. Derive
`capability_probe_identity_hash`. -> `CHEAPLUNA_PROVIDER_CAPABILITY_REPORT.json`. No capability
is asserted unless observed. If the model or endpoint is unavailable ->
`DEEPSEEK_DIRECT_PROVIDER_HOLD` (stop affected model work; keep local deterministic ops).

## 7. Phase P1B — Isolated BASELINE namespace + corpus/case freeze + executable baseline

### 7.1 Create the isolated BASELINE benchmark state namespace (BEFORE P1B)

Benchmark state isolation applies to the baseline as well as the candidate profiles. Before P1B,
create the isolated `BASELINE` benchmark state namespace with its own runtime-equivalent
scheduler.sqlite3, jobs/, cache/results/, worker-state, locks/, batches/, and negative-admission
state. Do NOT run P1B benchmark jobs through the active `perfume-chem-cheapluna-isolated` state.
The old scheduler must be exercised using ephemeral configuration pointed at the isolated BASELINE
state without changing scheduler semantics. If that cannot be done:
`DIRECT_DEEPSEEK_CURRENT_SCHEDULER_BASELINE_UNAVAILABLE`; `baseline_comparability: UNAVAILABLE`;
`PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`. Do not contaminate the active
project merely to obtain a baseline. Later create equivalently isolated `SAFE_NEW`,
`BALANCED_NEW`, and `TURBO_NEW` namespaces. Required: `cross_profile_scheduler_state_reuse: 0`;
`cross_profile_local_result_reuse: 0`.

### 7.2 Benchmark corpus and case freeze (BEFORE baseline)

Construct and freeze the complete benchmark corpus before running the baseline. For every packet
record: packet_id, task_class, exact decision request, exact source references, ordered source
SHA-256 values, expected deterministic result where applicable, allowed claims, prohibited
claims, abstention rule, local output schema identity, acceptance rule, timeout, output-token
ceiling. Additionally group the frozen corpus into independent benchmark cases; for every case
record: benchmark_case_id, task_class, packet_ids, dependency_edges, ordered_source_hashes,
acceptance_rule, case_start_definition, case_terminal_definition. Calculate
`BENCHMARK_CORPUS_SHA256` and record it, the case grouping, and the case count in the
authorization/pre-change evidence. The exact same semantic corpus identity is used by
`BASELINE_DIRECT_DEEPSEEK_CURRENT_SCHEDULER`, `SAFE_NEW`, `BALANCED_NEW`, and `TURBO_NEW`. Any
packet-content or source-hash change after P1B -> `BENCHMARK_CORPUS_DRIFT_HOLD`; do not compare
that run against the baseline.

### 7.3 Provider-cache namespace markers

DeepSeek provider-side context caching must not allow the baseline to warm the candidate profiles
unfairly. Assign every benchmark profile a stable, profile-specific provider-cache namespace
marker (BASELINE, SAFE_NEW, BALANCED_NEW, TURBO_NEW). The marker: is constant within that
profile; differs across profiles; is transport/benchmark metadata rather than scientific task
content; appears early enough in the request prefix to prevent cross-profile provider cache reuse;
and does not change the decision request, source hashes, allowed claims, prohibited claims, or
acceptance rule. Record its exact value and hash. The semantic benchmark corpus remains identical.
This result class is `PROVIDER_CACHE_ISOLATED_RESULT`.

### 7.4 Executable baseline

Run `BASELINE_DIRECT_DEEPSEEK_CURRENT_SCHEDULER`: OLD immutable runtime; current scheduler
implementation; direct DeepSeek provider; deepseek-v4-flash; the frozen packet corpus and case
grouping; exact source hashes; the isolated BASELINE state namespace; and the BASELINE
provider-cache namespace marker. **No new DAG scheduler, no new semantic cache, no new invocation
behavior, no new retry policy.** If current scheduler semantics must be changed to use direct
DeepSeek: `DIRECT_DEEPSEEK_CURRENT_SCHEDULER_BASELINE_UNAVAILABLE` — record the exact reason; do
not fabricate a comparable baseline.

Baseline promotion rule:
- If P1B succeeds: `baseline_comparability: COMPARABLE` — the P6E promotion gate uses it.
- If P1B is unavailable: `baseline_comparability: UNAVAILABLE` — SAFE_NEW / BALANCED_NEW /
  TURBO_NEW may still be executed for characterization, but no profile may claim
  `p95_improved_vs_current_scheduler` and no automatic profile promotion is authorized. Set
  `PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`; the fastest new profile may
  be reported as `UNPROMOTED_CANDIDATE` only. Never manufacture a baseline.

Historical DeepInfra metrics may be preserved only as `HISTORICAL_DEEPINFRA_REFERENCE`,
`NON_EXECUTED`, `NOT_PROMOTION_BASELINE`. DeepInfra provider calls during this upgrade: **0**.

## 8. Phase P2 — Routing + deterministic-local candidate changes (workspace-only)

1. Three semantic routes over the V4-Flash model:
   - `FLASH_FAST` (thinking off) -> recon / simple classification / source excerpt extraction /
     packet formatting / straightforward comparison.
   - `FLASH_HIGH` (thinking on, effort high) -> code review / failure diagnosis / source-authority
     comparison / architecture comparison / patch proposals / schema analysis.
   - `FLASH_MAX` (thinking on, effort max) -> final adversarial review / authority conflict
     adjudication / difficult root-cause / high-impact integration. Max reasoning never used for
     ordinary worker tasks.
2. Local-first classifier `DETERMINISTIC_LOCAL`: SHA-256, byte/file counts, path checks, ZIP
   validation, traversal checks, duplicate detection, JSON parse/schema, CSV validation,
   sorting, git status/diff, shard membership, test collection, pytest execution, count
   reconciliation, exact arithmetic. A deterministic task about to be sent to DeepSeek ->
   `DETERMINISTIC_TASK_MISROUTED`, reroute locally.
3. V4 tool-loop compatibility in the request builder: thinking-mode requests do **not** send
   `tool_choice` (`supports_tool_choice=false`); capture `reasoning_content` and preserve it on
   the assistant message for the following tool turn; preserve normal content and tool-call ids;
   return tool results against the correct call IDs; `reasoning_content` is transport state only,
   never surfaced as user output.
4. **Host-side candidate staging.** During P2-P5 do NOT mutate the live copies of
   `.opencode/scripts/cheapluna-bridge.ps1`, `cheapluna-cli.mjs`, `cheapluna-drain.mjs`,
   `delegation_pure.mjs`, `.opencode/plugins/cheapluna-cache-first.js`,
   `cheapluna-budget-guard.js`, `daemon-health-guard.js`, or `opencode.json`. Construct candidate
   versions under the upgrade workspace; test candidates against the candidate runtime where
   possible; record source SHA, candidate SHA, and proposed destination; preserve `pre_change`
   copies byte-for-byte. Live host-side copies are replaced only during cutover (P6B).
5. -> `CHEAPLUNA_ROUTING_POLICY.json` (candidate; also records the finite benchmark budget per
   section 17).

## 9. Phase P3 — Concurrency + DAG candidate changes (workspace-only)

1. Capacity: `max_normal_parallel_workers=4`, `reserved_slot=1` (health/audit). Reader lanes 4
   active + 1 reserved; writer lanes stay 1; `subagent_depth=1`; workers cannot spawn workers
   (every worker is a direct child of the parent orchestrator). The 4-worker ceiling is a local
   safety policy, not a provider limitation. -> `CHEAPLUNA_CONCURRENCY_POLICY.json` (candidate).
2. DAG micro-waves (wave driver over `lib/batch-dag.mjs` readyNodes/blocked):
   - Wave A: <=4 parallel scouts (SOURCE_SCOUT, TEST_SCOUT, CODE_SCOUT, CONTRACT_SCOUT).
   - Wave B: <=2 analysts (SYNTHESIS_ANALYST, ADVERSARIAL_ANALYST) — only after all required
     Wave-A outputs are COMPLETE, JSON-valid, source-hash-valid, non-quarantined.
   - Wave C: one fresh-context CRITICAL (`FLASH_MAX`) auditor, then one parent integration step.
   No downstream dispatch before dependencies are ready; no whole-repo reads per worker.
   -> `CHEAPLUNA_SCHEDULER_DAG.json` (candidate).

## 10. Phase P4 — Identity, prompts, semantic cache, packet contract (candidate, workspace-only)

1. Invocation identity: `logical_role` separated from `invocation_id` (`CL-20260807-000001`...);
   every launch emits exactly one provenance record with the required fields (invocation_id,
   logical_role, parent_invocation_id, packet_id, session_or_job_id, provider, requested_model,
   resolved_model, internal_model_label, thinking_state, reasoning_effort, source_hashes,
   prompt_hash, output_hash, start/end timestamps, latency_ms, cache hit/miss tokens,
   terminal_state). Never reuse w31/w32-style labels. Collision -> circuit breaker. ->
   `CHEAPLUNA_INVOCATION_IDENTITY_REPORT.json` (candidate).
2. Prompt prefix ordering (stable-first for provider cache reuse): governance contract ->
   scientific boundary contract -> role contract -> output schema -> shared source context sorted
   by source SHA-256 -> task question -> run ID -> invocation ID -> timestamp -> nonce. Volatile
   values last. Record hit/miss tokens per call; `cache_hit_ratio = hit/(hit+miss)` when
   denominator > 0. The provider-cache namespace marker (section 7.3) appears early in the stable
   prefix.
3. Local semantic result cache — resolved-model-identity key (all components): provider,
   api_model, returned_model, system_fingerprint_if_exposed, capability_probe_identity_hash,
   thinking_state, reasoning_effort, governance_prompt_sha256, worker_contract_sha256,
   output_schema_sha256, ordered_source_hashes, task_contract_version, decision_request_sha256.
   Excludes invocation_id/timestamp/nonce. Reuse only COMPLETE+VALIDATED+NON_QUARANTINED.
   Reused results emit a provenance event with `provider_call_performed:false` +
   `reused_output_hash`. If resolved model identity cannot be compared across runs, do not reuse
   semantic results across capability-probe epochs. -> `CHEAPLUNA_CACHE_REPORT.json` (candidate).
4. Packet minimization: one bounded decision per packet (packet_id, decision_requested,
   logical_role, source_hashes, source_material, allowed_claims, prohibited_claims,
   output_schema, abstention_conditions, acceptance_rule, timeout, max_output_tokens). ->
   `CHEAPLUNA_PACKET_CONTRACT.schema.json` (candidate).
5. Structured output schema: decision, evidence, source_hashes, conflicts, unknowns,
   abstention_reason, proposed_action, confidence_scope, terminal_state; explicit
   UNKNOWN / HOLD / INSUFFICIENT_EVIDENCE. Local validation; valid JSON but bad local schema ->
   `STRUCTURED_OUTPUT_SCHEMA_FAIL` (one repair only); semantic contradiction with exact source
   bytes -> `SEMANTIC_CORRUPTION` (no retry, quarantine).

## 11. Phase P5 — Retry, circuit breakers, single-writer, canary implementation (candidate, workspace-only)

1. `CHEAPLUNA_RETRY_POLICY.json`: 400/422 no retry unchanged; 401 AUTHENTICATION_HOLD;
   402 BALANCE_HOLD; 429 max two retries exponential backoff + jitter; 500 one retry;
   503 max two retries; network timeout one retry only when idempotent; schema-format failure
   one repair; semantic corruption zero retries; hash disagreement zero retries. Never switch
   provider after failure.
2. `CHEAPLUNA_CIRCUIT_BREAKER_POLICY.json`: quarantine on semantic_corruption>=1,
   source_hash_mismatch>=1, nested_worker_launch>=1, worker_invocation_id_collision>=1,
   canonical-write attempt>=1, overlapping canonical-write attempt>=1. On trigger: preserve
   request/response/source hashes/daemon logs; mark route QUARANTINED; native-host fallback;
   never erase evidence.
3. Single-writer: workers are advisory-only (analyze/classify/review/propose/scratch). Inside
   the isolated project: patches are proposals only; one designated parent/integrator applies
   changes sequentially with before/after hashes. No concurrent canonical writers.
4. Read/write canary implementations (executed in P6D and P6F): isolated disposable
   destinations only; byte- and SHA-verified; no path substitution; no extra bytes.

## 12. Phase P5B — Offline/unit/static validation of the COMPLETE candidate

Complete-candidate-first: P2, P3, P4, P5, P5B all run against candidate/workspace bytes. No
half-patched live runtime and no half-patched live host configuration. Run offline validation of
the complete candidate in the working copy: unit tests (`node --test`, incl. tool-loop
reconstruction regression), schema validation, hash reconciliation, routing classification
checks, retry-table checks, circuit-breaker trigger checks, provenance-record checks,
benchmark-corpus identity check (BENCHMARK_CORPUS_SHA256 unchanged), cache-namespace isolation
check, benchmark state-namespace isolation check, and provider-cache namespace marker check.
Iterate fixes inside the working copy. After P5B passes, compute the final candidate runtime
identity, install the immutable candidate runtime, verify its exact bytes — only then proceed to
cutover. **The live candidate daemon must never run a half-patched runtime.** ->
`CHEAPLUNA_TEST_REPORT.json` (offline portion).

## 13. Phase P6A — Install the final immutable candidate runtime

Recompute the runtime manifest over the patched working copy; compute the candidate runtime
identity; install a new immutable runtime directory named by the verified identity; validate all
candidate bytes (SHA-256 vs working copy, manifest hash equality, handshake constants). Only then
is the bridge cutover allowed. Old runtime remains READ_ONLY / IMMUTABLE.

## 14. Phase P6B — Controlled daemon cutover (incl. host-side files)

1 block new admissions; 2 inspect queue; 3 drain or terminally account pending jobs; 4 require
RUNNING == 0; 5 snapshot scheduler database; 6 stop old daemon gracefully; 7 verify old daemon
stopped; 8 verify all live target paths still match their pre-cutover expected hashes (drift ->
`CUTOVER_TARGET_DRIFT_HOLD`, do not overwrite); 9 install/apply the verified host-side candidate
files sequentially; 10 switch bridge runtime pin to the complete immutable candidate runtime;
11 start candidate daemon; 12 verify runtime build-identity handshake; 13 run daemon health
probe; 14 run direct-DeepSeek capability verification; 15 continue only on PASS (then reopen
admissions). Record before/after SHA-256 for every applied host-side path.
Rollback (on any candidate startup / handshake / host-side application / health / capability
failure): stop candidate daemon; restore exact host-side bytes from `pre_change`; restore bridge
pointer to the OLD immutable runtime; restart old daemon; verify old build identity; verify
restored host-side SHA-256 values; preserve all failed candidate evidence; record
`RUNTIME_CUTOVER_ROLLBACK`; keep admissions closed if health is uncertain; stop with HOLD.
Neither immutable runtime is modified during rollback.

## 15. Phase P6C — Live health + capability verification

After cutover: confirm daemon READY for `perfume-chem-cheapluna-isolated`, build-identity
handshake PASS, health probe PASS, and the direct-DeepSeek capability probe PASS before any
submission. Log results into `CHEAPLUNA_VALIDATION_REPORT.json` (live portion).

## 16. Phase P6D — PRE-BENCHMARK READ-INTEGRITY CANARY

After P6C passes and BEFORE the benchmark, run the READ canary. Native host creates
unpredictable controlled bytes; records exact SHA-256 and a nonce; forms the controlled advisory
packet. CheapLuna output is checked natively for expected nonce, exact required content identity,
source-hash correspondence, no substitution, no truncation disguised as success, and no invented
byte/line/base64 claims. Record `READ_CANARY_RESULT: PASS / FAIL` separately.
If READ canary fails -> `SEMANTIC_INTEGRITY_CANARY_FAIL`: do not run the 30+ packet benchmark; do
not promote SAFE/BALANCED/TURBO; preserve request/response/evidence; quarantine the affected
route; perform cutover rollback; stop with HOLD. **READ canary PASS is required before
benchmarking the candidate.**

## 17. Phase P6E — Benchmark: SAFE_NEW / BALANCED_NEW / TURBO_NEW (provider-cache isolated)

Only after READ canary PASS. Fixed corpus >=30 bounded packets (BENCHMARK_CORPUS_SHA256, frozen
in P1B) covering source discovery, code review, test diagnosis, schema review, authority
comparison, synthesis, adversarial audit — identical packets, case grouping, and source hashes to
P1B. Profiles: `SAFE_NEW` (2 workers), `BALANCED_NEW` (4 + 1 reserved), `TURBO_NEW` (4 scouts ->
<=2 analysts -> 1 max auditor), all on the candidate runtime with the same direct DeepSeek
provider, deepseek-v4-flash model, corpus, cases, source hashes, and profile-specific
provider-cache namespace markers.

Benchmark state isolation: do NOT execute comparative benchmark packets in the active
production-like CheapLuna project state. Create isolated benchmark state namespaces for BASELINE,
SAFE_NEW, BALANCED_NEW, TURBO_NEW, each with separate scheduler.sqlite3, jobs/, cache/results/,
worker state, locks/, batches/, and negative-admission state (or the exact runtime equivalent).
The active project `perfume-chem-cheapluna-isolated` must not accumulate benchmark jobs, cache
entries, locks, or worker state. Each namespace starts from a documented clean state appropriate
to the profile. `cross_profile_scheduler_state_reuse: 0`; `cross_profile_local_result_reuse: 0`.
Source files and the frozen benchmark corpus remain identical.

Provider-cache isolation: every profile carries a stable, profile-specific provider-cache
namespace marker (section 7.3) placed early in the stable request prefix. DeepSeek provider-side
context caching must not allow the baseline to warm the candidate profiles unfairly. The result
class used for promotion is `PROVIDER_CACHE_ISOLATED_RESULT`. Promotion decisions MUST use
`PROVIDER_CACHE_ISOLATED_RESULT`, not a cross-profile warmed result. Within-profile DeepSeek cache
reuse is allowed and measured. Separately, after the isolated comparison, an optional operational
pass may measure normal production cache behavior and report `WARM_OPERATIONAL_RESULT`; that class
is never used to prove the 10% scheduler promotion threshold. If equivalent provider-cache
isolation cannot be implemented for the old and new schedulers without altering their semantics:
`PROVIDER_CACHE_COMPARABILITY_UNAVAILABLE`; `PROFILE_PROMOTION_STATE:
PROMOTION_HOLD_NO_CACHE_COMPARABLE_BASELINE`; characterize the profiles but do not claim a causal
scheduler speedup. Record for every profile: prompt_cache_hit_tokens, prompt_cache_miss_tokens,
cache_hit_ratio, provider_cache_namespace_hash, and result_class.

Minimum critical-path sample count: predeclare
`minimum_critical_path_sample_count_for_promotion: 20`. Require at least 20 completed,
independently defined benchmark cases in BOTH the comparable baseline AND the candidate profile
being evaluated, using the exact same case IDs. If fewer than 20 comparable cases survive:
`PROFILE_PROMOTION_STATE: PROMOTION_HOLD_INSUFFICIENT_CRITICAL_PATH_SAMPLES`. Do not promote based
on worker-request p95, mean latency, or incomplete cases.

Case-level critical path: for every executed profile calculate `critical_path_ms` for each
independent benchmark case (defined in P1B). `p95_critical_path` is computed from the resulting
case-level `critical_path_ms` values — NOT from arbitrary individual model requests, tool calls,
queue events, or token-stream timings. Record `critical_path_sample_count` per profile.

Budget bound: before executing the >=30-packet benchmark, record a finite benchmark budget in
`CHEAPLUNA_ROUTING_POLICY.json`: max_provider_calls, max_output_tokens,
max_reasoning_tokens_if_measurable, max_deepseek_spend_or_equivalent_accounting, max_retries. Do
not raise a limit after observing results. If the bound is reached: `BENCHMARK_BUDGET_HOLD` —
stop additional benchmark calls and report partial results.

Metrics: e2e wall time, critical path (case-level), p50/p95 worker latency, model calls, avoided
calls, cache-hit/miss tokens + ratio, input/output/reasoning tokens, cost, accepted-output rate,
malformed-output rate, retries, 429s, semantic corruptions, hash mismatches, invocation-ID
collisions. -> `CHEAPLUNA_BENCHMARK_RESULTS.csv` + `CHEAPLUNA_BENCHMARK_REPORT.md`.

Promotion gate (predeclared; not decided after seeing results): a candidate may be promoted only
when ALL are true: `baseline_comparability == COMPARABLE`; `provider_cache_comparability ==
COMPARABLE`; `critical_path_sample_count >= 20`; `BENCHMARK_CORPUS_SHA256` unchanged; case IDs
identical; `cross_profile_scheduler_state_reuse == 0`; `cross_profile_local_result_reuse == 0`;
semantic_corruption == 0; source_hash_mismatch == 0; worker_invocation_id_collision == 0;
nested_worker_launch == 0; overlapping_canonical_write == 0;
`accepted_output_rate_new >= accepted_output_rate_baseline`; and
`p95_critical_path_new <= 0.90 * p95_critical_path_baseline`. Promotion statistic source:
`BENCHMARK_CASE_LEVEL_PROVIDER_CACHE_ISOLATED`. If multiple profiles pass, promote the lowest
case-level p95 critical path. If none pass: `PROFILE_PROMOTION_STATE:
NO_PROFILE_MET_PROMOTION_THRESHOLD`. If baseline unavailable:
`PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`. If sample size insufficient:
`PROFILE_PROMOTION_STATE: PROMOTION_HOLD_INSUFFICIENT_CRITICAL_PATH_SAMPLES`. If provider cache
comparability unavailable: `PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_CACHE_COMPARABLE_BASELINE`.
Do not promote from mean latency alone. Record exact evidence.

## 18. Phase P6F — WRITE canary (after benchmark)

Run the P5 WRITE canary against an isolated disposable destination only (no perfume-chem
canonical path): predetermined payload; byte-for-byte output; SHA-256; file existence; no extra
bytes; no path substitution. Record `WRITE_CANARY_RESULT: PASS / FAIL` separately. **Canaries
never auto-lift quarantine.** Regardless of result: `CHEAPLUNA_CANONICAL_IO: QUARANTINED`.
`CANONICAL_IO_QUALIFICATION_STATE: ELIGIBLE_FOR_SEPARATE_REVIEW` only if
`READ_CANARY_RESULT == PASS` AND `WRITE_CANARY_RESULT == PASS`; otherwise
`CANONICAL_IO_QUALIFICATION_STATE: NOT_ELIGIBLE`. This upgrade itself never authorizes canonical
IO. -> `CHEAPLUNA_CANARY_REPORT.json`.

## 19. Phase P7 — Outputs, validation, stop

1. Produce exactly these 22 artifacts in `.opencode/upgrades/CL-ORCH-UPGRADE-20260807-V1/`:
   1 CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json
   2 CHEAPLUNA_PRECHANGE_STATE.json
   3 CHEAPLUNA_PRECONDITION_SHA256SUMS.json
   4 CHEAPLUNA_PROVIDER_CAPABILITY_REPORT.json
   5 CHEAPLUNA_PROVIDER_CONFIG.json
   6 CHEAPLUNA_ROUTING_POLICY.json
   7 CHEAPLUNA_CONCURRENCY_POLICY.json
   8 CHEAPLUNA_SCHEDULER_DAG.json
   9 CHEAPLUNA_PACKET_CONTRACT.schema.json
   10 CHEAPLUNA_CACHE_REPORT.json
   11 CHEAPLUNA_RETRY_POLICY.json
   12 CHEAPLUNA_CIRCUIT_BREAKER_POLICY.json
   13 CHEAPLUNA_INVOCATION_IDENTITY_REPORT.json
   14 CHEAPLUNA_TOOL_LOOP_COMPATIBILITY_REPORT.json
   15 CHEAPLUNA_CANARY_REPORT.json
   16 CHEAPLUNA_BENCHMARK_RESULTS.csv
   17 CHEAPLUNA_BENCHMARK_REPORT.md
   18 CHEAPLUNA_FILES_CHANGED.csv
   19 CHEAPLUNA_TEST_REPORT.json
   20 CHEAPLUNA_HOLD_REGISTER.csv
   21 CHEAPLUNA_VALIDATION_REPORT.json
   22 CHEAPLUNA_SHA256SUMS.json — non-self-referential.
2. Run the validation checklist: only isolated-project allowlisted paths changed; PCV3 source
   paths changed = 0; worker invocation IDs unique; workers cannot spawn workers; one canonical
   writer; provider is direct DeepSeek; routes limited to LOCAL/FLASH_FAST/FLASH_HIGH/FLASH_MAX;
   no V4-Pro route active; no DeepInfra route active for this profile; DeepInfra calls = 0;
   V4-Pro calls = 0; fallback disabled; reasoning_content replay passes; thinking mode sends no
   tool_choice; deterministic tasks route locally; context-cache usage measured; semantic cache
   is content-addressed with resolved model identity; source hashes validated before downstream;
   retries bounded; semantic failures quarantine; benchmark corpus frozen before P1B and unchanged
   (BENCHMARK_CORPUS_SHA256); cross-profile local result-cache reuse = 0; cross-profile scheduler
   state reuse = 0; isolated BASELINE state namespace created before P1B; provider-cache namespace
   markers per profile recorded (value + hash); provider_cache_comparability recorded;
   critical_path_sample_count recorded; minimum_critical_path_sample_count_for_promotion = 20;
   critical-path statistic source = BENCHMARK_CASE_LEVEL_PROVIDER_CACHE_ISOLATED; benchmark
   namespaces removed or archived according to the upgrade evidence policy without modifying their
   recorded artifacts; READ canary PASS precedes benchmark; WRITE canary recorded separately;
   budget bound recorded before the run; promotion threshold predeclared; baseline exists before
   implementation (or exact unavailable reason recorded); host-side candidates staged without live
   mutation until cutover; cutover target paths verified against expected hashes; exact pre/post
   host hashes recorded; rollback restored bytes verified; rollback status explicit; canary
   history preserved; canonical IO not automatically unquarantined; credential safety respected
   (only credential_source_name / credential_present recorded; credential values never persisted);
   target-path provenance guard recorded per allowlist file.
3. Final state flags + `/plannotator-review` presentation: REV-3, REV-5, REV-6, and REV-7
   authority verification; REV-9 external receipt and EXTERNAL_SHA256_RECEIPT_VERIFICATION;
   pre-change state; target-path provenance; direct-DeepSeek capability results; benchmark corpus
   identity and case grouping; P1B baseline or exact baseline-unavailable reason; provider-cache
   namespace markers and provider_cache_comparability; exact runtime identity; exact host-side
   changes; tool-loop tests; READ canary; SAFE/BALANCED/TURBO results if READ canary passed;
   selected or unpromoted profile; WRITE canary; cache statistics (including
   PROVIDER_CACHE_ISOLATED_RESULT / WARM_OPERATIONAL_RESULT); budget/rollback state if any; hold
   register; validation report; SHA ledger. Then STOP — do not resume PCV3 Wave 2 automatically.

## 20. Holds & decision points (surfaced to user during execution)

- `PLAN_AUTHORITY_HOLD` — REV-3, REV-5, REV-6, or REV-7 authority verification mismatch, or
  EXTERNAL_SHA256_RECEIPT_VERIFICATION != PASS.
- `DEEPSEEK_DIRECT_PROVIDER_HOLD` — if deepseek-v4-flash @ api.deepseek.com is not observed in
  probes (report records observed reality only, no inference).
- `DIRECT_DEEPSEEK_CURRENT_SCHEDULER_BASELINE_UNAVAILABLE` — old scheduler cannot be exercised
  against direct DeepSeek without changing scheduler semantics; exact reason recorded; no
  fabricated baseline. -> `PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`.
- `PROVIDER_CACHE_COMPARABILITY_UNAVAILABLE` — equivalent provider-cache isolation cannot be
  implemented without altering scheduler semantics; characterize but do not claim a causal
  scheduler speedup. -> `PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_CACHE_COMPARABLE_BASELINE`.
- `BENCHMARK_CORPUS_DRIFT_HOLD` — packet content or source hashes changed after P1B; do not
  compare that run against the baseline.
- `BENCHMARK_BUDGET_HOLD` — benchmark budget bound reached; stop additional calls; report partial
  results; do not silently raise the budget.
- `NO_PROFILE_MET_PROMOTION_THRESHOLD` — no profile reached the predeclared 0.90 p95 improvement
  threshold; no promotion.
- `PROMOTION_HOLD_INSUFFICIENT_CRITICAL_PATH_SAMPLES` — fewer than 20 comparable case-level
  critical-path samples; characterize without promoting on the 10% rule.
- `RUNTIME_BUILD_INSTALL_HOLD` — new immutable runtime build cannot be installed; baseline runtime
  never patched.
- `RUNTIME_CUTOVER_ROLLBACK` — candidate daemon / handshake / host-side application / health /
  capability failure post-cutover; restore old immutable runtime + pre_change host bytes; upgrade
  stops with HOLD.
- `CUTOVER_TARGET_DRIFT_HOLD` — a live target path drifted from its pre-cutover expected hash;
  do not overwrite it.
- `SEMANTIC_INTEGRITY_CANARY_FAIL` — READ canary fails; no benchmark; quarantine route; rollback;
  HOLD.
- `TARGET_PATH_PROVENANCE_HOLD` — upgrade changes cannot be cleanly separated from pre-existing
  bytes in an allowlist file.
- `.cheapluna-home` vs `.opencode/.deepluna-home`: active is the latter; secondary home recorded
  only.
- Health-guard sqlite path mismatch in `daemon-health-guard.js` is fixed to the resolved active
  daemon.
- Upgrade dir `.opencode/upgrades/CL-ORCH-UPGRADE-20260807-V1/` (alternative: the pre-approved
  temp dir outside the repo) — confirm at execution start.
- Budget caps in `cheapluna-budget-guard.js` / `delegation_pure.mjs` are FLASH-oriented;
  FLASH_HIGH/FLASH_MAX need a revised envelope (output tokens, provider calls, cost) agreed in
  `CHEAPLUNA_ROUTING_POLICY.json`.
- Capability-probe epoch: semantic cache reuse is gated on resolved model identity across epochs.

## 21. Required final state

```
REV3_AUTHORITY_VERIFICATION:        PASS
REV5_EXECUTION_CONTRACT_VERIFICATION: PASS
REV6_EXECUTION_CONTRACT_VERIFICATION: PASS
REV7_EXECUTION_CONTRACT_VERIFICATION: PASS
EXTERNAL_SHA256_RECEIPT_VERIFICATION: PASS
CHEAPLUNA_PROVIDER:                DEEPSEEK_DIRECT
CHEAPLUNA_MODEL:                   deepseek-v4-flash
CHEAPLUNA_INTERNAL_LABEL:          DS-V4-FLASH-3107
CHEAPLUNA_ORCHESTRATION_UPGRADE:   COMPLETE / COMPLETE_WITH_HOLDS / PARTIAL / HOLD
BENCHMARK_CORPUS_SHA256:           <frozen identity>
READ_CANARY_RESULT:                PASS / FAIL
WRITE_CANARY_RESULT:               PASS / FAIL
CHEAPLUNA_CANONICAL_IO:            QUARANTINED (always; never auto-lifted by this upgrade)
CANONICAL_IO_QUALIFICATION_STATE:  ELIGIBLE_FOR_SEPARATE_REVIEW (only if both canaries PASS) / NOT_ELIGIBLE
cross_profile_local_result_reuse:  0
cross_profile_scheduler_state_reuse: 0
provider_cache_comparability:      COMPARABLE / UNAVAILABLE
provider_cache_promotion_result_class: PROVIDER_CACHE_ISOLATED_RESULT
minimum_critical_path_sample_count_for_promotion: 20
critical_path_sample_count:        <count>
critical_path_source:              BENCHMARK_CASE_LEVEL_PROVIDER_CACHE_ISOLATED
baseline_comparability:            COMPARABLE / UNAVAILABLE
PROFILE_PROMOTION_STATE:           PROMOTED / PROMOTION_HOLD_NO_COMPARABLE_BASELINE / PROMOTION_HOLD_NO_CACHE_COMPARABLE_BASELINE / PROMOTION_HOLD_INSUFFICIENT_CRITICAL_PATH_SAMPLES / NO_PROFILE_MET_PROMOTION_THRESHOLD
COLD_OR_ISOLATED_RESULT / WARM_OPERATIONAL_RESULT: reported where evidence supports both
PCV3_WAVE_2:                       NOT_STARTED
```
