# DeepLuna Chat Performance Hotfix — 2026-08-09

## Scope and authority

This hotfix applies to the Perfume-Chem non-Fast DeepLuna Chat route only:

- profile: `cheapluna-chat`;
- project: `perfume-chem-cheapluna-isolated`;
- allowed provider route: `DIRECT_PRO`;
- DeepLuna Fast: retired by the user;
- Sol: sole engineer and final acceptor;
- Codex subagents and provider fallback: not used.

## Reproduced failures

1. Initial worker contracts underestimated cumulative input-token bounds and
   were rejected locally before useful execution.
2. Correctly sized workers gathered evidence, but their final synthesis turn
   spent the complete 5,000-token response allowance on hidden reasoning and
   ended with `finish_reason=length` without a governed handoff.
3. A first non-thinking finalizer returned a citation object through free-form
   JSON; the normalizer converted it to `[object Object]`, correctly failing
   evidence acceptance.
4. The immutable installer copied the 22 hashed runtime files but omitted
   `node_modules`, so the first installed build could not start.
5. The CLI exposed `batch-submit` although production intentionally disables
   the legacy durable-batch validator. The original CLI also omitted the
   protocol's `{ input }` wrapper.

## Accepted runtime design

Evidence-gathering turns retain DeepSeek thinking, the bounded repository tools,
and required reasoning-content replay. Once all required reads are complete,
the runtime makes one final request with:

- thinking disabled;
- only the `finish_handoff` tool exposed;
- `tool_choice` forcing that exact tool;
- the complete governed handoff schema;
- citations required when coverage mode is `ALL_REQUIRED_READS`.

This follows the provider contract: response `max_tokens` includes reasoning,
while a named tool can be forced in non-thinking mode. See the official
[DeepSeek thinking-mode guide](https://api-docs.deepseek.com/guides/thinking_mode),
[chat-completion contract](https://api-docs.deepseek.com/api/create-chat-completion),
and [tool-call guide](https://api-docs.deepseek.com/guides/tool_calls).

The installer now reuses a dependency tree only when `package.json` and
`package-lock.json` are byte-identical to the candidate, then verifies every
top-level installed version against the lockfile. It performs no implicit
network installation.

The CLI now implements an explicit client-side fanout for fully independent,
read-only tasks. It submits each task through the authenticated `worker.submit`
RPC and lets the daemon's physical read lanes enforce capacity. It rejects
dependencies or partial-concurrency contracts instead of pretending to provide
durable batch semantics.

## Verification evidence

- Candidate contract suite: 25/25 passed.
- Isolated daemon/mock-provider suite: 11/11 passed.
- Current syntax checks: CLI, runtime, mock provider, installer, and contract
  harness passed `node --check`.
- Client-fanout dependency rejection: PASS. A dependency-bearing batch exited
  nonzero with the intended error; provider-transmission and job counters were
  unchanged before/after, proving no task or paid call was admitted.
- Live acceptance canary:
  - public job: `DS-973b08b2c07f97da44e2c3633ce0eb35`;
  - internal job: `DJ-efbde3b6-bf56-4a27-8ab1-fc7e2e41a01a`;
  - result: `PASS / ACCEPTED / POSITIVE / COMPLETE`;
  - evidence errors: 0;
  - provider turns: 2 (thinking read, then forced non-thinking handoff);
  - usage: 5,500 prompt tokens, 1,792 cached input tokens, 616 output
    tokens;
  - measured cost delta: approximately USD 0.000697.
- Four-worker V3 review: transport, topology, and security results passed and
  were independently checked by Sol. Both provenance outputs failed governance
  and were quarantined; neither was accepted or retried.
- Final authenticated health check:
  - runtime build:
    `150e46139d80a33e11da9cf37d9dd1b23acabe997c470902a90c29e7ce8bf80a`;
  - daemon PID: 24448;
  - release: 0.9.9;
  - readiness: `READY`;
  - active reads/writes/queue: 0/0/0;
  - read/write limits: 5/1;
  - open reservations: 0;
  - unknown reservations: 0.

## Remaining boundaries

- Client fanout is intentionally not durable batch state and supports only
  independent fully parallel tasks. Dependency graphs remain unavailable while
  the production legacy-batch validator is disabled.
- A `READY` daemon authorizes no task by itself. Every provider transmission
  still requires an exact-project health/accounting check and a bounded,
  non-sensitive task contract.
- ChatGPT reciprocal-link notices and filesystem-app attachment are separate
  product surfaces. The latter remains blocked until the active organization
  context is repaired and the remote connector release canary passes.

## Follow-up packed-input sizing finding

The G15 stock-authority review exposed one caller-side sizing pitfall after the
runtime hotfix. Job `DS-855978d1441720eb380ce69e3d66359d` selected 11,530 bytes
of required file evidence, but the daemon estimated 34,231 provider input tokens
after adding the fixed orchestration prompt, schemas, and tool contract. The
caller's 24,000-token input ceiling therefore rejected the job before a review
was produced. This was a correct fail-closed rejection, not a provider outage.

Retry `DS-db6878115afb32cc1edfbf3ac42ca9dd` kept the same evidence, route,
two-call limit, and no-fallback policy while raising only the explicit aggregate
token envelope; it reached a terminal review. Future task builders should keep
the 15 KiB required-read cap but budget against the daemon's packed-input
estimate, not infer the provider input solely from selected source bytes.
