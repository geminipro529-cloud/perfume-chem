# Build C2 Matrix and Application-Environment Gate

Decision: **PASS**

C2 is accepted. The matrix and application-environment contract, evidence-only
seal commit, final DeepLuna Fast audit, Sol reconciliation, and postcommit
verification all passed. C3 is open; Build C and scientific release remain
incomplete.

## Implemented boundary

The committed C2 layer adds:

- five distinct matrix stages;
- ten component roles and six explicit quantity bases;
- exact, partial, and unresolved composition states with explicit missing fields;
- versioned component and matrix snapshots with deterministic SHA-256 hashes;
- all nine required application-environment kinds;
- typed dose, area, film geometry, substrate, temperature, humidity, airflow,
  timing, sampling, vessel, and headspace fields;
- explicit separation of missing and not-applicable environment fields;
- sealed-vial apparatus/sampling requirements;
- a matrix-aware model request that embeds both complete snapshots, repeats both
  context hashes, verifies nested hashes on parse, and has its own deterministic
  request hash.

The module evaluates no physical equation, creates no prediction or measurement,
does not adapt `MixtureState` or `SolventLedger`, and changes no production
physical-model caller.

## C2 exit behavior

The synthetic contract fixture uses one formula hash and produced these request
hashes:

| Context | Request SHA-256 |
| --- | --- |
| Baseline | `1896223a579eee5668737f590aa3afff767584db2c474fca9d3a821e956a7896` |
| Matrix changed | `e22c6925264d084a3c5951c1f1ea3e9e0cc3070cd208c5748bc7db18cdb55970` |
| Environment changed | `dcf7dcf6cdb9b3717afad2e884aaed9d0af4808eb786f19fb9800aaf4520c45e` |

All three request hashes are distinct. The receipt is explicitly a contract
fixture, not a physical prediction or measurement.

## Verification

The first captured gate run correctly failed the complete suite: the explicit
truth-core shard manifest omitted the C0, C1, and new C2 test files. Focused C2,
C1, and C0 tests were already green. Commit
`193d5546fa1bebbfd16c152f4f2fc80dec053987` added exactly those three manifest
entries. The shard invariant then passed.

The final committed-tree capture reports:

- C2 focused: 79 passed;
- C1 compatibility: 96 passed;
- C0 compatibility: 24 passed;
- complete root suite: 1297 passed;
- Ruff check: pass;
- Ruff format check: 3 files already formatted;
- basedpyright: 0 errors, 0 warnings, 0 notes;
- mypy: no issues in the C2 module;
- all command stderr streams empty;
- no timeout.

The original Ruff captures contained ANSI because `FORCE_COLOR=0` still enables
forced color for that tool. Those logs are retained as historical evidence and
are not gate-bearing. The authoritative Ruff rerun removed `FORCE_COLOR`, exited
zero, and contains zero ANSI bytes. Across the authoritative final log set there
are zero ANSI bytes, invalid UTF-8 files, or credential-pattern matches.

## Recovery, protected state, and scope

The path-preserving prewrite archive is 118,417,920 bytes with SHA-256
`35325c26d526619623ce1c2f05c72484ad8377ed534f488b4191a2e7e649d023`.
All 444 manifest entries matched length and digest; no unsafe or duplicate tar
members were found. All 429 archived Git-visible dirty/untracked paths still
match their prewrite bytes. The manifest records 1,203 excluded DeepLuna runtime
paths.

`perfume_chem.db` and `data/perfumery_kb.db` retain their pre-C2 lengths and
SHA-256 values, and both read-only SQLite quick checks return `ok`.

The committed C2 phase changed seven paths: design, plan, the C2 contract module,
the aggregate package export, the C2 test, a two-line C1 export-compatibility
assertion, and the three-entry verifier shard manifest. It changed no migration,
database, generated scientific artifact, production physical caller,
`MixtureState`, or `SolventLedger` path.

## DeepLuna and acceptance

The fresh exact-project preflight was `READY` for project `perfume-chem`, release
0.9.9, runtime build
`32973174a8440053d723dc660e1ed4c7c38544c6b1014649a8f3d2e176bc4f11`,
with zero active reads/writes/queue and zero open or unknown reservations.

Final-audit job `DS-bb8a02b0461b50d363bda5755b983ae3` returned `PASS`,
`POSITIVE`, and `ACCEPTED` with no negative findings, scope deviation,
architecture uncertainty, or scientific uncertainty. It used one `FLASH` call
to `deepseek-ai/DeepSeek-V4-Flash` through DeepInfra priority service, with
`NO_LUNA`, no cache hit, 52,739 total tokens, and a reconciled cost of 7,217,100
nanoUSD. Postflight remained `READY` with zero active/queued work and zero open
or unknown reservations; Luna, GLM, and Codex orchestration remained unused.

The compact terminal status truncated one positive-finding string and exposed no
file citations. Sol therefore accepted no unsupported provider claim and
independently reproduced the enum counts and values, matrix and environment
validation, nested hashes, same-formula distinguishability, no-equation boundary,
scope, archive, protected-state, and captured-log evidence. The audit is
supplemental; canonical repository state and locally reproduced executable
evidence remain authoritative.

The evidence-only seal is commit
`dba6f856d099d5abd6250b9feb5df75cf20bde36`, whose 71 changed paths are all
under `docs/verification/c2`. Its parent is the verified implementation commit
`193d5546fa1bebbfd16c152f4f2fc80dec053987`.

Postcommit replay against that exact evidence commit passed all 14 bounded
commands: C2 79, C1 96, C0 24, complete root 1,297, Ruff check and format,
basedpyright, and mypy. All stderr streams are empty, no command timed out, and
the postcommit capture contains zero ANSI bytes, invalid UTF-8 files, or
credential-pattern matches. The archive re-hashed correctly, both SQLite quick
checks returned `ok`, and all 429 pre-existing dirty/untracked files still match
their prewrite bytes.

C2 therefore passes and C3 is open. This decision does not complete Build C or
authorize scientific release.

## Limitations

- no equation evaluation or unit conversion;
- no solvent-loss or time-evolution simulation;
- no prediction or measurement value;
- no automatic legacy adapter;
- no production caller migration;
- no scientific-release authority;
- Build C remains incomplete.
