# Build B7 claim authority gate

Status: **PASS**

Recorded: 2026-08-02 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Implementation head: `ff1542a02f3564f602ecf7f2ae1e93e4f6e103b9`

Verification checkpoint before this report:
`2d5136a3f1afca2458cc403423eb68db4afb2642`

## Current outcome

The local B7 gate, bounded final report audit, and Sol postflight are green.
The exact B7 evidence commit remains the seal required before B8 begins.

B7 converts exact canonical B2-B6 evidence versions into an append-only,
reconstructable, claim-specific authority decision. It never trusts caller
authority booleans, never averages away a critical failure or unknown, and
never promotes incomplete or context-mismatched support.

The exact decision vocabulary is:

- `ALLOW_EXACT`
- `ALLOW_SCOPED`
- `ADVISORY_ONLY`
- `WITHHOLD_UNKNOWN`
- `BLOCK`

Every decision preserves supporting observations, conflicts, limitations,
missing requirements, source references, uncertainty, and permitted and
forbidden language. `release_authority` is always false. B7 is not release
authority, legal advice, a safety certificate, or proof of real-world
performance.

## Claim and sufficiency coverage

The current implementation has code-owned policies for all eleven required
claim types:

1. exact chemical identity
2. grade identity
3. property value
4. threshold
5. above-threshold screening
6. analytical identification
7. analytical quantitation
8. natural constituent profile
9. knowledge-rule recommendation
10. regulatory screening
11. formula or model comparison

Each policy evaluates required fields, accepted evidence classes, identity and
condition scope, minimum coverage, source independence, contradictions,
uncertainty, method validation, model applicability, safety, and wording.
Typed support links preserve `SUPPORTING`, `CONTRADICTING`, and `LIMITATION`
roles against exact B2-B6 canonical versions.

The migration `20260731_0011` creates two empty append-only tables and imports
zero legacy rows:

1. `lab_claim_authority_versions`
2. `lab_claim_authority_support_links`

Policy, direct-upstream, link, and authority hashes make each result
reconstructable. Revision lineage preserves claim type, subject, identity,
condition, and claim scope. Stronger evidence upgrades only that scoped claim.

## Historical defects rechecked

The historical implementation once allowed a `PARTIAL` natural profile to
promote to `ALLOW_SCOPED`. It also initially lacked explicit integration tests
for speculative or unknown evidence, `LIMITATION`-only support, and missing
required fields. The current focused gate includes all four fail-closed paths
and passes them; no current production-code change was required.

## Current executable evidence

Supported runtime and migration state:

- Python `3.11.15`
- Node `v26.3.0`
- phase revision `20260731_0011`
- single current Alembic head `20260731_0012`
- non-PTY execution, ANSI disabled, explicit timeouts, and separate stdout and
  stderr captures

Focused B7 schema, service, migration, and end-to-end gate:

```text
58 passed in 124.72s (0:02:04)
```

Exit code was `0`; stderr is empty.

Cumulative 29-file A2 through B7 compatibility, migration, and backup/restore
gate:

```text
324 passed in 612.11s (0:10:12)
```

Exit code was `0`; stderr is empty.

Static gates:

- Ruff over 13 B7/shared-registration paths: `All checks passed!`, exit `0`
- mypy over the B7 model, repository, and service: `Success: no issues found
  in 3 source files`, exit `0`

Accepted streams are stored under `docs/verification/b7/logs/` as UTF-8
without BOM. The raw PowerShell captures remain outside the repository, and
the JSON report binds every accepted stream hash.

## Migration and protected database proof

Executable tests cover prior-head upgrade, two empty B7 tables, exact typed
foreign keys, constraints, indexes, append-only guards, zero prior-row import,
downgrade/re-upgrade, reconstruction, lineage, scope immutability, current-head
tracking, and backup/restore.

Current repository migration state is the later linear head `20260731_0012`;
B7 remains revision `20260731_0011` in that chain.

| Path | Bytes | SHA-256 | Integrity |
|---|---:|---|---|
| `perfume_chem.db` | 12288 | `02B64BE88E4A8881C968EC9EF7F0185ED7B1BCEDC6ED33885F07D7DE70A0DA5E` | `quick_check=ok`; no Alembic rows |
| `data/perfumery_kb.db` | 2084864 | `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1` | immutable read-only `quick_check=ok`; no Alembic rows |

Both protected databases remained byte-identical before and after the gate.
No migration was applied to either database.

## Recovery and worktree preservation

The complete prior B7 report/log tree was archived before refresh:

`outputs/b7-authoritative-recovery/20260802T084938/b7-evidence-before-refresh-verified.zip`

- bytes: `20049`
- SHA-256:
  `0F23D3E41EDCF05E403B5417FA91BB3F44D89BB7BA12116AEE68B57102B6C3DA`
- path-preserving files: `19`
- unsafe archive members: `0`
- restore verification: `19/19` extracted files matched source SHA-256

Two wrapper diagnostics are excluded from backup evidence. The first stopped
before creating a file because the ZIP enum assembly was unavailable. The
second created only a 22-byte empty ZIP shell before discovering that Windows
PowerShell lacks `Path.GetRelativePath`. Both touched no B7 evidence; the
distinct verified archive above is the accepted backup.

Before the report edit, the preserved overlay had 109 tracked dirty paths,
1,308 untracked files, and zero staged entries. No cleanup, reset, migration,
artifact regeneration, or production-code edit was performed. The eight
phase-owned B7 implementation/test paths have no delta from `ff1542a`.

## DeepLuna use and authority boundary

A fresh exact-project check returned `READY` for `perfume-chem`, runtime
`CANDIDATE_V2`, release `0.9.9`, with zero active reads/writes, an empty queue,
zero open or unknown reservations, and provider calls enabled.

The bounded gap audit `DS-2a94046a19579e81ee17fee5448e68dd`
returned `PASS/POSITIVE/ACCEPTED` and correctly identified the contract's
eleven claim types, five decisions, typed support, and fail-closed tests. Its
recommendation that no current-evidence gaps existed was rejected: the worker
was deliberately restricted to historical documents and did not inspect the
current Alembic head, protected databases, executable tests, or worktree. Sol
found and replaced the stale 2026-07-31 head, duration, and zero-byte database
claims through local verification.

The final report audit `DS-2929cefabadbb69e51b37656d0c60957`
returned `PASS/POSITIVE/ACCEPTED` with one Fast provider call, no negative
findings, no scope deviation, and no required correction. Its measured usage
was 16,134 prompt tokens, 648 completion tokens, and 2,353,050 nano-USD. The
redacted receipt is
`docs/verification/b7/logs/deepluna-current-final-audit.json` (1,412 bytes;
SHA-256
`AD27CA0FF992E1E9AC54CF42924FAAD2890453F6B658AAFDE19D460C769357F4`).

A fresh post-provider check again returned exact-project `READY` with zero
active reads/writes, an empty queue, and zero open or unknown reservations.
DeepLuna remains supplemental; Sol retains architecture, scope, provenance,
security, and final acceptance.

## Exit gate

The B7 evidence package passes its substantive exit gate:

1. fresh exact-project DeepLuna preflight and postflight are `READY`;
2. the bounded Fast-only report audit returned accepted positive evidence;
3. Sol reproduced every final-audit finding and rejected the earlier gap
   audit's unsupported current-state conclusion;
4. focused, cumulative, lint, typing, migration, database, report, log, source,
   and archive checks pass; and
5. no production code or protected database changed during reverification.

The exact B7 evidence paths must now be committed with no unrelated staging.
B8 must not begin before that seal commit exists.
