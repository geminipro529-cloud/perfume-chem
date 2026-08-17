# DeepLuna Chat Fail-Closed Project Scheduler Design

- **Date:** 2026-08-17
- **Status:** Approved architecture; implementation not started
- **Project:** `perfume-chem-cheapluna-isolated`
- **Route:** `cheapluna-chat / DIRECT_PRO / NO_LUNA`

## 1. Decision Summary

DeepLuna Chat will use one durable, fail-closed project scheduler as the sole
authority for task admission, queueing, exact single-flight, authenticated
origin isolation, writer conflict control, provider-transmission accounting,
and recovery.

The existing daemon and SQLite ledger will be extended. A thin admission client
may submit and monitor work, but it must not implement a second scheduler,
maintain competing queue truth, or infer per-job cost from process-wide health
deltas.

The target capacity is:

- up to 128 authenticated pipe connections;
- up to 50 logical read lanes;
- up to 10 concurrent writer lanes when their declared scopes do not overlap;
- one independently governed paid-provider transmission window, initially
  conservative and raised only to a separately accepted canary level; and
- serialized durable ledger transitions where SQLite consistency requires it.

“Auto approve all tasks” means automatic scheduler admission only for tasks
that satisfy every declared eligibility check. It does not grant scientific,
release, package-promotion, destructive, irreversible, credential, security,
or final-acceptance authority. Ineligible or ambiguous work fails closed with a
specific terminal or held reason.

No runtime activation is authorized by this document. Activation requires both
a provider-free real-pipe verification and a separately reviewed and accepted
bounded paid canary.

## 2. Context and Proven Baseline

The current project route is isolated to DeepLuna Chat with `DIRECT_PRO` and
`NO_LUNA`; Fast, Luna, Codex orchestration, and alternate provider fallback are
out of scope and remain disabled.

The installed immutable runtime has already demonstrated these useful baseline
properties:

- authenticated origin-bound sessions;
- exact-task single-flight behavior;
- durable provider-transmission accounting;
- 128 configured pipe connections;
- 50 logical read lanes and 10 logical writer lanes; and
- a provider-free 50-client connectivity pass.

That evidence proves connection and logical-lane capacity, not safe paid
provider concurrency. A historical 50-job paid wave produced only 12 accepted
jobs while 38 jobs were quarantined with `STALE_ATTEMPT_LEASE`. Therefore the
safe paid-provider window is unproven and must not be equated with the pipe,
read-lane, or writer-lane limits.

The existing drain script is not suitable as production scheduling authority.
It submits a whole wave concurrently, attributes job cost through shared health
deltas, treats dependency release mainly as logging, retries polling failures
without a sufficiently bounded ambiguity policy, and checkpoints registry
state only at wave boundaries. Those behaviors would create competing truth
and race-prone accounting if retained as a scheduler.

## 3. Goals

1. Maximize safe throughput for many concurrent Codex tasks in one exact
   project.
2. Preserve one authoritative queue, lease, single-flight, and accounting
   state.
3. Permit many read tasks and up to ten non-conflicting write tasks without
   weakening provenance or authority boundaries.
4. Prevent duplicate paid work for exact duplicate task contracts.
5. Isolate each authenticated origin’s status, result, cancellation, and
   subscription rights.
6. Account cumulatively and exactly for every provider transmission.
7. Recover deterministically after client, daemon, or pipe interruption.
8. Fail closed on ambiguity, receipt drift, unknown accounting, stale leases,
   route drift, scope conflicts, or unauthorized authority requests.
9. Prove the scheduler over the real pipe without provider traffic before any
   paid canary.
10. Activate only the exact immutable build that passed all required gates.

## 4. Non-Goals

- Re-enabling DeepLuna Fast, Luna, Codex orchestration, or provider fallback.
- Treating connection capacity as evidence of safe paid concurrency.
- Automatically retrying an ambiguous provider timeout.
- Automatically promoting scientific claims, physical observations, packages,
  canonical data, releases, or irreversible changes.
- Replacing SQLite with another store or introducing a parallel broker.
- Mutating the installed immutable runtime in place.
- Solving unrelated Perfume-Chem repository or Chat 2 dark-material work.
- Claiming scientific, sensory, physical, or release results from software
  verification.

## 5. Architecture

### 5.1 Sole scheduler authority

The daemon owns all durable scheduling state:

- admission state;
- queued, leased, running, held, quarantined, and terminal state;
- dependency readiness;
- exact single-flight producer and subscriber bindings;
- read- and writer-lane allocation;
- normalized writer-scope conflicts;
- provider-transmission reservations and reconciliation;
- authenticated origin ownership;
- restart recovery; and
- audit events.

Clients may submit contracts, query only their authorized work, and receive
events. A client may not independently release dependencies, assign lanes,
retry ambiguous work, calculate authoritative cost, or reconstruct scheduler
truth from logs.

### 5.2 Capacity planes

Capacity is split into independent planes so that one successful plane cannot
silently authorize another:

| Plane | Target | Governing rule |
|---|---:|---|
| Authenticated pipe connections | 128 | Transport capacity only |
| Logical read lanes | 50 | Read-only task admission and local orchestration |
| Logical writer lanes | 10 | Exact, non-overlapping declared scopes only |
| Paid provider transmissions | Canary-derived | Never inferred from the limits above |
| SQLite durable transitions | Serialized as required | Correctness before throughput |

The paid-provider window starts at the highest separately accepted clean canary
stage. It may be reduced immediately after an anomaly. It may be increased only
by a new accepted bounded canary, not by uncontrolled online auto-tuning.

### 5.3 Thin admission client

The existing drain behavior will be replaced or reduced to a thin client that:

1. authenticates to the exact project;
2. submits a canonical task contract;
3. receives a stable job or subscriber identifier;
4. follows daemon-issued state transitions;
5. reattaches after interruption; and
6. reports daemon receipts without reinterpreting them.

The client must not use unbounded `Promise.all` submission as a substitute for
scheduler admission, and must not derive per-job cost from before/after global
health values.

## 6. Canonical Task Contract and Admission

Each task contract must include enough normalized information to make
eligibility and exact reuse deterministic:

- exact project identity;
- route and provider profile;
- server-derived authenticated origin identity, never a client-trusted claim;
- task kind and authority class;
- canonical task input;
- relevant input, receipt, configuration, and resource hashes;
- dependency identifiers;
- read or writer mode;
- exact normalized writer paths or resources when applicable;
- declared budget and transmission policy;
- timeout and ambiguity policy;
- verification and rollback contract for writes; and
- cache eligibility rules.

Admission runs in this order:

1. authenticate origin and bind the request to the exact project;
2. verify the pinned route and runtime profile;
3. validate and canonicalize the task contract;
4. compute the exact task fingerprint from all relevant contract inputs;
5. reject receipt, resource, or configuration drift;
6. check exact local cache eligibility;
7. attach to an existing exact single-flight producer when allowed;
8. verify durable budget reservation and accounting readiness;
9. apply read-lane or writer-scope admission rules;
10. enforce authority exclusions;
11. persist the admission transition; and
12. issue the stable job or subscriber receipt.

Any missing, contradictory, unauthenticated, stale, or ambiguous field causes a
hold or rejection. No best-effort normalization may broaden task scope.

## 7. Exact Single-Flight and Origin Isolation

### 7.1 Exact producer identity

Only tasks with the same exact project, route, normalized contract, relevant
hashes, authority class, and provider policy may share a producer. A near match
is a different task.

When an exact producer already exists, a new eligible request becomes a
subscriber. It does not create another provider transmission. Cache reuse is
allowed only when the completed receipt and all relevant current hashes still
match.

### 7.2 Subscriber isolation

Each subscriber remains bound to its authenticated origin. The scheduler must
deny cross-origin status reads, result reads, event streams, cancellation,
scope changes, and receipt access unless an explicit project policy grants that
specific capability.

Coalescing work does not merge origin authority. A shared producer publishes a
result once, and the scheduler makes that accepted result visible separately to
each authorized subscriber.

Cancellation semantics must be explicit:

- canceling one subscriber detaches only that subscriber;
- the producer may be canceled only when no authorized subscriber remains and
  cancellation is safe;
- an in-flight ambiguous provider transmission is never silently retried; and
- one origin cannot cancel another origin’s subscription.

## 8. Read and Writer Scheduling

### 8.1 Read lanes

Eligible read-only tasks may run across up to 50 logical lanes. Read-only means
the declared task cannot mutate repository files, project stores, remote state,
provider configuration, releases, or authority-bearing records.

Read capacity may continue operating while conflicting writers are queued, as
long as the read contract does not depend on a partially written resource.

### 8.2 Writer lanes

An automatically admitted writer must declare:

- exact normalized destination paths or resource keys;
- its worktree or isolation boundary;
- expected precondition hashes;
- a bounded rollback strategy;
- its verification command or receipt contract; and
- whether readers must be fenced during publication.

The daemon builds a conflict graph from normalized paths and resources.
Non-overlapping writers may run concurrently up to ten lanes. Overlapping or
ancestor/descendant scopes queue behind one another; they are not launched and
then retried after collision.

Writer scope is immutable after admission. Any discovered write outside the
declared scope fails closed, quarantines the task receipt, and blocks automatic
publication. A task requiring destructive, irreversible, release, canonical
promotion, credential, or scientific authority remains manual regardless of
path non-overlap.

## 9. Per-Transmission Accounting

Every provider transmission has its own durable identity and lifecycle:

1. persist a reservation before the request leaves the process;
2. bind it to project, job, generation, attempt, turn, provider request, and
   authenticated origin or producer identity;
3. record dispatch without reusing another transmission’s receipt;
4. reconcile actual usage and cost exactly once;
5. preserve cumulative totals from immutable transmission records; and
6. release or quarantine the reservation through a durable terminal
   transition.

Process-wide health deltas are diagnostic only and must never be authoritative
per-job attribution.

Unknown or contradictory transmission state blocks further provider calls for
the affected project until deterministically reconciled. A client timeout does
not prove that a provider call failed. Ambiguous calls are held without
automatic retry to prevent duplicate paid work.

Accounting acceptance requires:

- no unowned reservations;
- no duplicate provider request identity;
- no negative or decreasing cumulative totals;
- exactly one terminal reconciliation per dispatched transmission;
- agreement between transmission records and project cumulative totals; and
- explicit quarantine for any unresolved mismatch.

## 10. Lease Diagnosis and Repair

The historical `STALE_ATTEMPT_LEASE` failure must be reproduced using a
deterministic fake provider through the real scheduler path before a repair is
selected.

Instrumentation must distinguish at least:

- heartbeat scheduling delay;
- event-loop lag;
- SQLite lock or transaction wait;
- provider response latency;
- queue wait versus active attempt time;
- lease generation or ownership mismatch;
- daemon restart or pipe interruption; and
- terminal event publication delay.

The implementation must first add a failing regression that reproduces the
observed class of stale lease under bounded stress. The smallest repair that
addresses the measured cause is then implemented. Lease duration inflation,
heartbeat changes, transaction restructuring, or concurrency reduction are
possible outcomes, but this design does not predetermine which is correct.

No increase in paid-provider concurrency is authorized merely because the
regression passes with a fake provider. Paid capacity remains canary-derived.

## 11. Durable Recovery

The daemon ledger is the sole recovery source. Clients reattach by stable job
or subscriber identifier and authenticated origin.

After daemon restart, the scheduler must deterministically classify:

- queued work;
- active leases;
- dispatched but unreconciled transmissions;
- exact single-flight producers and subscribers;
- writer-scope ownership;
- reservations; and
- terminal results pending publication.

Work with provably safe state may resume. Orphaned, unknown, expired, or
ambiguous state is held or quarantined. Restart must not create a replacement
provider transmission for a request that may already have been dispatched.

The thin client keeps no authority-bearing shadow checkpoint. Local client
state may accelerate reattachment but cannot override the daemon ledger.

## 12. Automatic Admission Boundaries

Automatic admission is allowed only for:

- authenticated, exact-project tasks;
- validated read-only contracts; and
- fully scoped, non-conflicting, reversible writer contracts with bounded
  verification and no reserved authority class.

Manual authority remains required for:

- scientific interpretation or acceptance;
- claims based on physical, sensory, stability, safety, or measured evidence;
- canonical data or package promotion;
- release or deployment acceptance;
- destructive or irreversible actions;
- credentials, security policy, or origin-policy changes;
- paid concurrency increases; and
- final acceptance by Sol.

Automatic admission removes repetitive human prompts for eligible work. It does
not convert a software receipt into scientific, physical, package, release, or
architectural authority.

## 13. Provider-Free Real-Pipe Verification Gate

Verification runs against a new immutable candidate runtime through the actual
named-pipe transport and authentication path. The provider is replaced by a
deterministic fake that records attempted calls. Acceptance requires zero real
provider calls, tokens, and cost.

The gate must verify:

1. exact candidate manifest and SHA-256 ledger;
2. exact project and route pinning;
3. authenticated multi-origin connection handling;
4. 50 concurrent logical readers;
5. 10 concurrent non-conflicting writers;
6. deterministic queueing of conflicting writer scopes;
7. exact duplicate coalescing into one fake producer call;
8. no coalescing for near-match contracts;
9. denied cross-origin status, result, cancellation, and subscription access;
10. per-transmission reservation and exactly-once reconciliation;
11. accounting fault injection that fails closed;
12. deterministic stale-lease regression and repair;
13. client disconnect and reattachment;
14. daemon restart and ledger recovery;
15. ambiguous dispatch recovery without automatic retry;
16. dependency ordering controlled by the daemon;
17. clean shutdown and quiescence; and
18. database integrity, foreign-key integrity, zero active leases, zero active
    reservations, and zero unexplained unknown states after quiescence.

The gate produces a versioned manifest, test report, event and accounting
receipts, SHA-256 ledger, and immutable candidate identifier. Passing this gate
does not authorize a paid canary; it only makes the candidate eligible for
separate canary review.

## 14. Separately Accepted Paid Canary

The paid canary uses only bounded, non-sensitive, read-only tasks with exact
contracts and explicit cost ceilings. It begins only after the provider-free
gate is accepted.

The initial ladder is:

1. one transmission;
2. two concurrent transmissions;
3. five concurrent transmissions;
4. ten concurrent transmissions; and
5. optionally 15, 20, 30, 40, and 50 only if each preceding stage is clean and
   separately accepted.

The first stage proves end-to-end identity and accounting. Each concurrency
increase after that must have at least two consecutive clean bounded waves
unless the acceptance authority records a stricter requirement.

Every stage stops immediately on:

- any stale lease;
- duplicate or unexplained provider transmission;
- unknown or unreconciled accounting;
- origin isolation failure;
- timeout ambiguity;
- writer-scope conflict;
- receipt, route, runtime, or input drift;
- cost or token mismatch;
- provider fallback; or
- unexpected terminal-state disagreement.

There is no automatic retry or fallback. The highest independently accepted
clean stage becomes the production paid-provider window. Pipe and logical lane
capacity remain unchanged and do not raise that window.

## 15. Observability and Error Handling

Each job must expose, only to authorized origins:

- stable project, job, producer, and subscriber identities;
- canonical task fingerprint;
- current state and terminal reason;
- dependency state;
- assigned read or writer lane;
- normalized writer scope and conflict reason;
- cache or single-flight disposition;
- provider transmission and reservation identities;
- reserved and actual cumulative usage and cost;
- lease generation and heartbeat timing;
- runtime build, route, and relevant input hashes; and
- verification and publication receipts.

Logs and receipts must not contain secrets, credentials, raw authentication
tokens, or another origin’s protected task content. Diagnostic summaries may
aggregate counts only when they cannot reveal protected origin data.

Errors use explicit fail-closed classes, including authentication failure,
project mismatch, route drift, contract drift, writer conflict, unauthorized
authority, budget unavailable, accounting unknown, stale lease, ambiguous
dispatch, verification failure, and recovery quarantine.

## 16. Test Strategy

Implementation follows test-driven development:

1. add the focused failing test for one behavior;
2. confirm it fails for the expected reason;
3. implement the smallest repair;
4. run the focused test;
5. run the related contract suite; and
6. retain deterministic receipts for concurrency gates.

Required coverage includes:

- task canonicalization and fingerprint boundaries;
- exact and near-match single-flight behavior;
- subscriber cancellation semantics;
- origin authentication and cross-origin denial;
- read-lane limits;
- normalized writer conflict graphs;
- undeclared-write quarantine;
- dependency admission;
- reservation, dispatch, reconciliation, and cumulative accounting;
- duplicate and ambiguous provider dispatch protection;
- stale-lease reproduction and repair;
- disconnect, restart, and orphan recovery;
- immutable runtime pinning; and
- the complete provider-free real-pipe gate.

No paid test is used where a deterministic fake-provider test can establish the
same software property.

## 17. Deployment and Rollback

1. Build a new immutable candidate; never patch the installed runtime in place.
2. Produce an exact manifest, candidate hash, dependency inventory, and
   validation ledger.
3. Run focused tests and the provider-free real-pipe gate.
4. Obtain separate acceptance for a bounded paid canary.
5. Run and review the canary ladder only to the accepted level.
6. Pin the exact accepted runtime and paid-provider window.
7. Restart the exact project daemon through the protected launcher.
8. Verify daemon identity, route, ledger health, reservations, lane limits, and
   postflight accounting.
9. Preserve the previous immutable runtime and pin as the rollback target.

Rollback is triggered by any post-activation invariant failure. New provider
work stops first, ambiguous transmissions remain held, the last accepted
runtime pin is restored, and ledger reconciliation is completed before work
resumes. Rollback must not erase or rewrite transmission history.

## 18. Acceptance Criteria

The scheduler is eligible for activation only when all of the following are
true:

- one daemon and one SQLite ledger are the only scheduling authority;
- the client contains no competing queue, lease, dependency, or cost truth;
- exact single-flight prevents duplicate provider work;
- authenticated origins cannot access or control one another’s subscriptions;
- 50 readers and 10 non-conflicting writers pass the provider-free real-pipe
  gate;
- writer conflicts queue deterministically and undeclared writes fail closed;
- every provider transmission is reserved and reconciled exactly once;
- cumulative accounting replays from transmission records;
- stale-lease behavior has a deterministic regression and verified repair;
- restart recovery never automatically retries ambiguous dispatched work;
- the immutable candidate passes manifest, test, pipe, ledger, and hash checks;
- a separate bounded paid canary is explicitly accepted;
- the production paid-provider window equals no more than the highest accepted
  clean canary stage; and
- scientific, physical, package, release, destructive, security, and final
  authority boundaries remain manual and unchanged.

## 19. Risks and Tradeoffs

- A single scheduler simplifies truth and recovery but makes daemon correctness
  critical; immutable builds, durable receipts, and rollback mitigate this.
- SQLite serialization can limit write throughput; correctness is retained and
  concurrency is spent on independent work around short transactions.
- Exact single-flight may reduce apparent job count while increasing useful
  throughput by eliminating duplicate paid work.
- Strict writer scopes require better task contracts, but prevent silent
  cross-task corruption.
- Conservative paid canaries may delay reaching maximum provider fanout, but
  connection capacity alone is insufficient evidence after the historical
  stale-lease wave.
- Origin isolation adds bookkeeping for shared producers, but coalescing must
  never imply shared authorization.

## 20. Authority Boundary

This design authorizes documentation and subsequent implementation planning
only. It does not authorize runtime changes, provider transmissions, daemon
activation, repository-wide integration, scientific acceptance, package
promotion, release, or any physical-result claim.

Sol remains the sole architecture, security, science, provenance, release, and
final-acceptance authority. DeepLuna workers may provide bounded evidence, but
their output cannot promote itself.
