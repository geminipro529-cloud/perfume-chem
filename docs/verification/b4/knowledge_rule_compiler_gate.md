# Build B4 Knowledge-Rule Compiler Gate

Decision: **PASS**

Implementation authority:
`edab5112d69ca34fc96e2af15e7e5ee30f7e34e4` and
`0b274a4b5ef8648c795e37ebdab1baabc8192b81`.

This gate covers Build B Phase B4 only. It does not implement analytical
authority (B5), regulatory authority (B6), claim sufficiency (B7),
decision-value backfill (B8), production consumers (B9), or the Build B
release audit (B10).

## Implemented canonical contract

- Six append-only tables store versioned rule groups and members, rules,
  contradictions, controlled support evidence, and compilation runs.
- Exact endpoints require identity-scope digests; groups require explicit
  group versions. Generic prose and unresolved references can be explanatory
  or advisory but cannot become authoritative, blocking, or numerical.
- Database checks require every `AUTHORITATIVE` rule or group to carry exact
  source-version, extraction, locator, and approved-review provenance.
- Only authoritative rules can block. Numerical interaction models require
  controlled evidence with matching identity, matrix, and dose domains.
- The compiler preserves stable diagnostics, retains duplicates as inventory
  evidence, labels only edges inside cyclic strongly connected components,
  rejects null required digests, and exposes transparent recommendation
  projections without formula-mutation commands.
- The migration imports zero legacy groups, rules, contradictions, support
  records, or compilation runs. Production consumers remain disconnected
  until B9.

## Frozen legacy-corpus regression

The adapter inventories all 3,381 records from the four frozen JSON sources.
Its deterministic report is
`C49A49DD2BAC5FB0B819E2162FBB60E851A098925F7680EA7C920650B7E75FB7`:
137 invalid exact records, 68 duplicates, one directed-cycle diagnostic, zero
blocking rules, and zero numerical models.

Sol found that identical rule-source hashes produced 137 invalid exact records
under the authoritative resolver but 138 under a stale scratch resolver.
The baseline had therefore left identity-resolution results ambient. B4 now
commits a 454-label resolution snapshot (SHA-256
`51D4A70E...09014`) as an explicit, non-authoritative regression input. It is
not a runtime registry and cannot confer identity authority. After that fix,
the stale scratch environment also passed the complete 129-test slice.

## Fresh canonical verification

All accepted commands ran non-interactively under supported Python 3.11.15,
with ANSI disabled, explicit timeouts, and separate stdout/stderr logs under
`docs/verification/b4/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr |
|---|---:|---|---|
| B1+B2+B3+B4+compatibility pytest | 129 passed in 139.16 s | `ED23EB6C...6E2B3` | empty |
| Ruff, exact B4 paths | all checks passed | `82B3E6A6...B4F18` | empty |
| Mypy, four B4 modules | no issues | `D9A5631F...7BB76` | empty |

An earlier pytest invocation used the read-only canonical directory as its
working directory. Because `conftest.py` uses a relative SQLite test database,
that invocation produced 32 setup errors with “attempt to write a readonly
database.” It was rejected as gate evidence. The unchanged suite was rerun
from an isolated writable working directory and passed 129/129.

The protected root `perfume_chem.db` remains zero bytes with SHA-256
`E3B0C442...B855`. `data/perfumery_kb.db` remains 2,084,864 bytes with
SHA-256 `5A779F9D...3FE1`; an immutable read-only SQLite connection reports
integrity `ok`.

## Independent review and DeepLuna boundary

DeepLuna remained Fast-only (`FLASH`, `NO_LUNA`) and no Codex subagent was
used. The migration-risk job
`DS-29a34bf13ae71b1a7222cb6cadb9cbbf` returned PASS but contradicted itself
about the existing B3 downgrade after an incomplete read, so Sol rejected that
claim and relied on executable downgrade tests.

The postimplementation audit
`DS-5c335f5f0b80291a1ee1890a4391fe56` also returned PASS with no defects.
Sol independently reproduced three defects it missed:

- direct database inserts could bypass authoritative provenance;
- one directed cycle labeled independent rules as cyclic; and
- required compilation and payload digests accepted null.

RED tests reproduced all three. Database constraints, SCC-scoped cycle
handling, and required-digest validation now close them. Sol then found and
closed the separate ambient-resolver reproducibility defect. DeepLuna evidence
remains supplemental; canonical source, tests, constraints, frozen inputs,
and independently reproduced behavior are final authority.

## B4 exit decision

Exact rules now resolve only to canonical identity digests or explicit groups.
Invalid, generic, unresolved, and advisory records are separated from blocking
logic. Generic prose cannot silently change a formula. Numerical interaction
models cannot be promoted without controlled matching evidence. The complete
legacy regression is input-bound and deterministic, model/migration parity and
downgrade/re-upgrade pass, and protected databases are unchanged.

Therefore B4 passes without claiming that any legacy rule is scientifically
true, production-ready, or release-authorizing.

## Protected state and recovery

- The A0 full recovery package remains preserved.
- Four path-preserving B4 archives cover initial implementation, canonical
  prepromotion, the three-defect postfix, and the resolver-snapshot postfix.
- Archive SHA-256 values are recorded in the machine-readable report.
- Every archive was extracted separately; all present-path hashes matched and
  absent-path manifests matched.
- After the two implementation commits, the pre-existing worktree still had
  105 tracked dirty paths, 615 untracked files, and zero staged entries.

## Limitations and claim boundary

- The 454-label snapshot is regression evidence only, not identity authority.
- The legacy inventory still contains 137 invalid exact records, 68
  duplicates, and one cycle diagnostic; none is blocking.
- No production API, UI, optimizer, or recommendation consumer is connected.
- No legacy row is auto-promoted by migration.
- The DeepLuna PASS missed defects found by Sol, so provider output is not
  accepted as final authority.
- Scientific release remains **BLOCKED**.

B5 may begin under its own RED tests and exit gate.
