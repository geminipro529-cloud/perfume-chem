# CHEAPLUNA ORCHESTRATION BEHAVIOR UPGRADE — CL-ORCH-UPGRADE-20260807-V1

## 0.0 Revision metadata

revision_id: REV-6
plannotator_review_id: PR-20260807-CL-ORCH-V1-R6
governing_plan: REV-5 (APPROVE_CL_ORCH_REV5_EXECUTION) body 31518 / 7c04da3bd0c6dbe2ed6de93a75bdcfc22b1650ca5909b9b8b6cab2e6ae0d18c2; whole 32311 / 498afa5417d10a046c42a42694e91f8d242c7665102e5e40c8ad209cdf295c73
underlying_plan: REV-3 (APPROVE_CL_ORCH_REV3_EXECUTION) body 24305 / 57a914d0c1bb10c180cee83afe8fffd6f4bb1517bcd60b5d7a81b69be1f8a459; whole 25287 / 9c8d3ac7c7419ab17d0997e1d932510c6e3a9829023d4471c7b23fb2d12d37b8
supersedes: REV-4 (NON_EXECUTABLE_HASH_MISMATCH — declared hashes did not reproduce from the exact final file)
body_byte_size: 36485
body_sha256: 24497ebcf2a1fec38ba83f0700f620ef8fbe442f20f004095fc14f70251e9e1c
whole_file_byte_size: 37492
whole_file_sha256: f0ba18b73144ca3dc2efe1a2ec6b9d6334f0eed6419daf0410eaa5235d2797a8
hash_note_body: body_sha256 is computed per the approved convention: body starts at `## 0. Intent`, metadata and the preceding `---` separator excluded, exactly one terminal LF removed, UTF-8, no BOM, LF-normalized.
hash_note_whole: whole_file_sha256 is the SHA-256 of the complete Markdown file (title, revision metadata, separator, all sections, final-state block) with the whole_file_sha256 value replaced by exactly 64 ASCII zeroes, exactly one terminal LF removed, UTF-8, no BOM, LF-normalized. It is the execution authority; any subsequent byte change requires a new revision and review.
hash_self_verification: PASS (regenerated from the exact final REV-6 file; independent verifier reproduced all four metadata values; recorded in CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json)

---

## 0. Intent

Upgrade the CheapLuna delegation layer (direct DeepSeek provider lock, V4 tool-call
compatibility, three V4-Flash semantic routes, local-first deterministic routing, 4+1
concurrency, DAG micro-waves, unique invocation IDs, cache-reuse prompt ordering, local
semantic result cache, packet minimization, structured outputs, bounded retries, circuit
breakers, single-writer, canaries, old-vs-new benchmark) while preserving exact source
fidelity, single-writer behavior, deterministic validation, abstention, provenance, and the
existing canonical-IO quarantine.

REV-3 was approved for execution (`APPROVE_CL_ORCH_REV3_EXECUTION`). REV-4 integrated the
binding execution directives but was declared NON_EXECUTABLE_HASH_MISMATCH because its declared
canonical hashes did not reproduce from the exact final file. REV-5 was approved as the exact
integrated execution contract (`APPROVE_CL_ORCH_REV5_EXECUTION`). REV-6 integrates the 13 binding
execution directives into the phase plan without changing REV-5's approved content. The REV-3 and
REV-5 authority verification and the REV-6 HASH_SELF_VERIFICATION result are recorded in
`CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json`.

**PCV3 FREEZE is respected throughout.** No PCV3 source, test, run, inventory, formula, or
planning artifact is touched. `PCV3_WAVE_2` stays `NOT_STARTED`.

## 0.1 Execution authorization (binding)

- Underlying governing plan REV-3 (verified): canonical body 24305 bytes / SHA-256
  `57a914d0c1bb10c180cee83afe8fffd6f4bb1517bcd60b5d7a81b69be1f8a459`; canonical whole-file
  25287 bytes / SHA-256 `9c8d3ac7c7419ab17d0997e1d932510c6e3a9829023d4471c7b23fb2d12d37b8`.
- Approved execution contract REV-5 (verified): canonical body 31518 bytes / SHA-256
  `7c04da3bd0c6dbe2ed6de93a75bdcfc22b1650ca5909b9b8b6cab2e6ae0d18c2`; canonical whole-file
  32311 bytes / SHA-256 `498afa5417d10a046c42a42694e91f8d242c7665102e5e40c8ad209cdf295c73`.
- Authority gates: `REV3_AUTHORITY_VERIFICATION: PASS` and
  `REV5_EXECUTION_CONTRACT_VERIFICATION: PASS` are required before any modification; both
  identities are recorded in the authorization artifact. Otherwise -> `PLAN_AUTHORITY_HOLD`; stop
  before writes.
- REV-6 integrity metadata (body_byte_size, body_sha256, whole_file_byte_size,
  whole_file_sha256) was computed from the exact final REV-6 file and reproduced by a second
  independent verifier. HASH_SELF_VERIFICATION = PASS is recorded in the authorization artifact.
- Canonicalization convention (recorded in the authorization artifact): UTF-8; no BOM; normalize
  CRLF and CR to LF; replace the whole_file_sha256 value with exactly 64 ASCII zeroes; the
  canonical whole-file serialization includes title, metadata, separator, all sections, and the
  final-state block; remove exactly one terminal LF if present before calculating byte size and
  SHA-256. Body = from `## 0. Intent` to end; metadata and preceding separator excluded; one
  terminal LF removed before hashing.
- The 13 binding execution directives (benchmark corpus freeze before P1B; cache isolation;
  predeclared promotion threshold; budget bound; separate READ/WRITE canary results; canonical-IO
  qualification rule) are integrated into the phases below and are binding.

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

## 5. Phase P0 — Freeze guard + dual authority verification + immutable snapshots

1. Assert PCV3 freeze (no writes outside the section 2 allowlist; log a marker).
2. Verify the underlying governing plan REV-3 under its declared convention. Mismatch ->
   `PLAN_AUTHORITY_HOLD`; stop. Record `REV3_AUTHORITY_VERIFICATION: PASS`.
3. Independently verify the approved execution contract REV-5 under its declared convention.
   Mismatch -> `PLAN_AUTHORITY_HOLD`; stop. Record `REV5_EXECUTION_CONTRACT_VERIFICATION: PASS`.
4. Resolve section 1 into `CHEAPLUNA_PRECHANGE_STATE.json` (live daemon PID, sqlite mtime, build hash).
5. Build immutable `CHEAPLUNA_PRECONDITION_SHA256SUMS.json` (non-self-referential).
6. Copy all modifiable files into `pre_change/` (byte-for-byte).
7. Run the target-path provenance guard (section 3) and record classifications.
8. `CHEAPLUNA_ORCHESTRATION_UPGRADE_AUTHORIZATION.json` (records REV-3 and REV-5 identities,
   REV-6 HASH_SELF_VERIFICATION, canonicalization convention, PCV3 freeze, allowlist,
   credential_source_name / credential_present only).

## 6. Phase P1A — Direct DeepSeek capability probe (OLD immutable runtime, current scheduler)

Bounded harmless probes A-D against `api.deepseek.com` via the OLD immutable runtime's direct
profile, with the CURRENT scheduler untouched: A thinking disabled; B thinking enabled / effort
high; C thinking enabled / effort max; D thinking + one harmless tool-call loop. Record
requested vs returned model, system_fingerprint (if exposed), HTTP status, first-token + total
latency, thinking state, reasoning effort, tool-call behavior, JSON validity,
prompt_cache_hit/miss_tokens, input/output/reasoning tokens. Derive
`capability_probe_identity_hash`. -> `CHEAPLUNA_PROVIDER_CAPABILITY_REPORT.json`. No capability
is asserted unless observed. If the model or endpoint is unavailable ->
`DEEPSEEK_DIRECT_PROVIDER_HOLD` (stop affected model work; keep local deterministic ops).

## 7. Phase P1B — Benchmark corpus freeze + executable baseline BEFORE implementation

### 7.1 Benchmark corpus freeze (BEFORE baseline)

Construct and freeze the complete benchmark corpus before running the baseline. For every packet
record: packet_id, task_class, exact decision request, exact source references, ordered source
SHA-256 values, expected deterministic result where applicable, allowed claims, prohibited
claims, abstention rule, local output schema identity, acceptance rule, timeout, output-token
ceiling. Calculate `BENCHMARK_CORPUS_SHA256` and record it in the authorization/pre-change
evidence. The exact same semantic corpus identity is used by `BASELINE_DIRECT_DEEPSEEK_CURRENT_
SCHEDULER`, `SAFE_NEW`, `BALANCED_NEW`, and `TURBO_NEW`. Any packet-content or source-hash change
after P1B -> `BENCHMARK_CORPUS_DRIFT_HOLD`; do not compare that run against the baseline.

### 7.2 Executable baseline

Run `BASELINE_DIRECT_DEEPSEEK_CURRENT_SCHEDULER`: OLD immutable runtime; current scheduler
implementation; direct DeepSeek provider; deepseek-v4-flash; the frozen packet corpus; exact
source hashes. **No new DAG scheduler, no new semantic cache, no new invocation behavior, no new
retry policy.** This baseline MUST complete before routing/scheduler/cache/retry/DAG behavior is
modified. If direct DeepSeek cannot be exercised by the old scheduler without changing its
scheduler semantics: `DIRECT_DEEPSEEK_CURRENT_SCHEDULER_BASELINE_UNAVAILABLE` — record the exact
reason; do not fabricate a comparable baseline.

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
   denominator > 0.
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
benchmark-corpus identity check (BENCHMARK_CORPUS_SHA256 unchanged), and cache-namespace
isolation check. Iterate fixes inside the working copy. After P5B passes, compute the final
candidate runtime identity, install the immutable candidate runtime, verify its exact bytes —
only then proceed to cutover. **The live candidate daemon must never run a half-patched runtime.**
-> `CHEAPLUNA_TEST_REPORT.json` (offline portion).

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

## 17. Phase P6E — Benchmark: SAFE_NEW / BALANCED_NEW / TURBO_NEW

Only after READ canary PASS. Fixed corpus >=30 bounded packets (BENCHMARK_CORPUS_SHA256, frozen
in P1B) covering source discovery, code review, test diagnosis, schema review, authority
comparison, synthesis, adversarial audit — identical packets and source hashes to P1B. Profiles:
`SAFE_NEW` (2 workers), `BALANCED_NEW` (4 + 1 reserved), `TURBO_NEW` (4 scouts -> <=2 analysts ->
1 max auditor), all on the candidate runtime with the same direct DeepSeek provider,
deepseek-v4-flash model, corpus, and source hashes.

Benchmark cache isolation: do NOT let one profile receive local semantic-result-cache answers
generated by another profile. Use separate local semantic-cache namespaces for BASELINE, SAFE_NEW,
BALANCED_NEW, TURBO_NEW, or disable cross-profile result reuse during the comparative benchmark.
`cross_profile_local_result_reuse: 0`. Within-profile warm-cache reuse may be measured separately
when intentionally testing warm-cache behavior. Provider-side DeepSeek context caching is not
assumed resettable; record per profile prompt_cache_hit_tokens, prompt_cache_miss_tokens,
cache_hit_ratio, and cold/warm status where determinable, and report `COLD_OR_ISOLATED_RESULT`
and `WARM_OPERATIONAL_RESULT` where evidence supports both. Do not attribute a latency difference
solely to scheduler behavior when provider cache conditions materially differ.

Budget bound: before executing the >=30-packet benchmark, record a finite benchmark budget in
`CHEAPLUNA_ROUTING_POLICY.json`: maximum provider calls, maximum aggregate output tokens, maximum
aggregate reasoning tokens where measurable, maximum DeepSeek spend or equivalent budget
accounting, and maximum retries. If the bound is reached: `BENCHMARK_BUDGET_HOLD` — stop
additional benchmark calls and report partial results; do not silently raise the budget during
the run.

Metrics: e2e wall time, critical path, p50/p95 worker latency, model calls, avoided calls,
cache-hit/miss tokens + ratio, input/output/reasoning tokens, cost, accepted-output rate,
malformed-output rate, retries, 429s, semantic corruptions, hash mismatches, invocation-ID
collisions. -> `CHEAPLUNA_BENCHMARK_RESULTS.csv` + `CHEAPLUNA_BENCHMARK_REPORT.md`.

Promotion threshold (predeclared; not decided after seeing results): when
`baseline_comparability: COMPARABLE`, promotion requires all REV-5 correctness gates
(semantic_corruption==0, source_hash_mismatch==0, worker_invocation_id_collision==0,
nested_worker_launch==0, overlapping_canonical_write==0) PLUS
`p95_critical_path_new <= 0.90 * p95_critical_path_baseline` (at least 10 percent lower p95
critical-path latency) AND `accepted_output_rate_new >= accepted_output_rate_baseline`. If
multiple profiles pass, select the fastest passing profile by p95 critical path; p50 and cost are
secondary diagnostics. If no profile reaches the predeclared improvement threshold:
`PROFILE_PROMOTION_STATE: NO_PROFILE_MET_PROMOTION_THRESHOLD` — do not promote merely because one
profile is numerically fastest. If `baseline_comparability: UNAVAILABLE`: no automatic promotion;
`PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`; fastest new profile reported as
`UNPROMOTED_CANDIDATE` only. Record exact evidence.

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
   (BENCHMARK_CORPUS_SHA256); cross-profile local result-cache reuse = 0; READ canary PASS
   precedes benchmark; WRITE canary recorded separately; budget bound recorded before the run;
   promotion threshold predeclared; baseline exists before implementation (or exact unavailable
   reason recorded); host-side candidates staged without live mutation until cutover; cutover
   target paths verified against expected hashes; exact pre/post host hashes recorded; rollback
   restored bytes verified; rollback status explicit; canary history preserved; canonical IO not
   automatically unquarantined; credential safety respected (only credential_source_name /
   credential_present recorded; credential values never persisted); target-path provenance guard
   recorded per allowlist file.
3. Final state flags + `/plannotator-review` presentation: REV-3 and REV-5 authority verification;
   REV-6 HASH_SELF_VERIFICATION; pre-change state; target-path provenance; direct-DeepSeek
   capability results; benchmark corpus identity; P1B baseline or exact baseline-unavailable
   reason; exact runtime identity; exact host-side changes; tool-loop tests; READ canary; SAFE/
   BALANCED/TURBO results if READ canary passed; selected or unpromoted profile; WRITE canary;
   cache statistics (including COLD_OR_ISOLATED_RESULT / WARM_OPERATIONAL_RESULT); budget/rollback
   state if any; hold register; validation report; SHA ledger. Then STOP — do not resume PCV3
   Wave 2 automatically.

## 20. Holds & decision points (surfaced to user during execution)

- `PLAN_AUTHORITY_HOLD` — REV-3 or REV-5 authority verification mismatch.
- `DEEPSEEK_DIRECT_PROVIDER_HOLD` — if deepseek-v4-flash @ api.deepseek.com is not observed in
  probes (report records observed reality only, no inference).
- `DIRECT_DEEPSEEK_CURRENT_SCHEDULER_BASELINE_UNAVAILABLE` — old scheduler cannot be exercised
  against direct DeepSeek without changing scheduler semantics; exact reason recorded; no
  fabricated baseline. -> `PROFILE_PROMOTION_STATE: PROMOTION_HOLD_NO_COMPARABLE_BASELINE`.
- `BENCHMARK_CORPUS_DRIFT_HOLD` — packet content or source hashes changed after P1B; do not
  compare that run against the baseline.
- `BENCHMARK_BUDGET_HOLD` — benchmark budget bound reached; stop additional calls; report partial
  results; do not silently raise the budget.
- `NO_PROFILE_MET_PROMOTION_THRESHOLD` — no profile reached the predeclared 0.90 p95 improvement
  threshold; no promotion.
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
baseline_comparability:            COMPARABLE / UNAVAILABLE
PROFILE_PROMOTION_STATE:           PROMOTED / PROMOTION_HOLD_NO_COMPARABLE_BASELINE / NO_PROFILE_MET_PROMOTION_THRESHOLD
COLD_OR_ISOLATED_RESULT / WARM_OPERATIONAL_RESULT: reported where evidence supports both
PCV3_WAVE_2:                       NOT_STARTED
```
