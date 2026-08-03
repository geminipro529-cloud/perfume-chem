# Build D Phase D0 claim-matrix exit gate

Status: **PASS for the D0 software gate only**.

Verified implementation state: `de5e1ef72fa9f78c00aa46c0e3c48a32a870166f` on
`codex/add-inventory-materials`. D1 has not started. This result does not
authorize a human study, mixing either formula, product release, or a validated
sensory/scientific claim.

## D0 outcome

The implementation defines exactly 17 claim families and an explicit allowed
method policy for each family. The contracts are immutable and versioned and
carry claim scope, comparator, endpoints, decision criteria, evidence
requirements, authority state, and revalidation triggers. Authority is fixed
fail-closed: `study_authorized=false`, `release_authority=false`, and
`observed_outcome=unmeasured` (`engine/scientific_validation/contracts.py:263`).

The first planning claim is
`D0-PRADA-ORRIS-INTERVENTION-001` version 1. It binds the quarantined Prada
control and luxury-Orris artifacts by exact SHA-256, uses a trained descriptive
panel at a standardized 30-minute blotter condition, defines an orris-intensity
primary endpoint with a provisional lower margin of `+0.50`, and protects the
clean pressed-shirt/soapy, wood-amber, and dryness/balance attributes with a
provisional equivalence interval of `[-0.75, +0.75]`
(`engine/scientific_validation/first_claim.py:29`,
`engine/scientific_validation/first_claim.py:188`). The 12 evidence requirements
and 8 revalidation triggers are planning requirements, not collected evidence.

The live verifier independently reads the current formula bytes and status
headers, refuses changed hashes or non-quarantined status, requires the Orris
carrier gap to remain visible, checks all D0 exit fields, and emits
`d1_started=false` (`scripts/verify_d0_claim_matrix.py:49`,
`scripts/verify_d0_claim_matrix.py:145`,
`scripts/verify_d0_claim_matrix.py:236`).

## Executable evidence

All commands used Python 3.11 from `.venv_py311_a0`, no PTY, disabled pytest
color/cache, external temp/cache paths, separate stdout and stderr, and explicit
timeouts. The authoritative capture is:

`C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\d0-gate-20260803T123746212`

| Check | Result | Timeout | stderr | stdout SHA-256 |
|---|---:|---:|---:|---|
| D0 focused tests | 20 passed | 300 s | 0 bytes | `10c3091f7057b9ee174deb78ef5948a5bdfd949b17a7226f8033805782a6cd27` |
| C0-through-D0 matrix | 675 passed | 900 s | 0 bytes | `61732496d84807da30d20e9415a6bd374cd455d46fcff3cec2ea81f83aeb56bc` |
| Full root suite | 1,773 passed | 1,200 s | 0 bytes | `eab6550c6023dee81671e4fdc94e5099d964a31df7a000a263acff57e19b70af` |
| Ruff D0/integration scope | pass | 300 s | 0 bytes | `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18` |
| mypy D0/integration scope | 6 files, no issues | 300 s | 0 bytes | `90377c8fd97127580c93ac5740d596c9ebc9db94dafa6560ee11fe16b4460c62` |
| Live verifier A | exit 0 | 120 s | 0 bytes | `f8f1ea622e6b406a95930570a32c3da34af09c97d78e659dd76d96a0c7fccf1b` |
| Live verifier B | exit 0 | 120 s | 0 bytes | `f8f1ea622e6b406a95930570a32c3da34af09c97d78e659dd76d96a0c7fccf1b` |

The two verifier runs were byte-identical. Their payload reports 17 families,
all six required D0 exit fields, 12 required evidence items, exact quarantined
formula hashes, provisional margins, `scientific_outcome=unmeasured`, and
`d1_started=false`.

The first broad replay found one D0-caused integration defect: the new test file
was absent from the canonical shard manifest. A new RED test reproduced that
failure; commit `de5e1ef72fa9f78c00aa46c0e3c48a32a870166f` registered D0 in the
`truth-core`, lint, and typecheck checks. The final 1,773-test replay passed. A
separate intermediate run whose outer desktop allowance expired before final
metadata was excluded from acceptance even though its full-root child output
was green.

## Preservation and scope

Before D0 writes, a path-preserving archive captured the existing worktree:

- Archive: `D:\.backups\perfume-chem\build-d0-prewrite-20260803T115425+0700.tar`
- Size: 118,281,728 bytes
- SHA-256: `a94928628805538cf34138de92bb0dda4886f3d1216b934057e9ed4138ee76b2`
- Manifest: 432 files, including all 429 non-runtime dirty/untracked files
- Verification: zero unsafe members, duplicates, archive mismatches, or current
  mismatches
- Restore proof: all 432 files restored with zero mismatches under the short
  Windows path `D:\.backups\perfume-chem\d0rv-20260803T115425`

After D0, the protected status remains exactly 1,782 entries with the same
normalized SHA-256
`4487309377de170c3dc1edf71022f16133806be81f142c305fa894e14efdf532` and
zero staged files. Six protected files match the pre-D archive byte-for-byte;
`backend/app/models/lab_claims.py` was clean rather than archived and retains
the identical pre-D/current Git blob
`da7b6ec8f08c48aca98d1611ac6eb8d3640a6f95`. The nine committed D0 paths
contain no database, migration, SQL, or database-file path.

## Independent Fast audit

Fresh exact-project preflight was `READY` for
`workspace-712a446e211c45e1b9d1`, with zero open or unknown reservations.
DeepLuna Fast job `DS-2f8a54df95b4b62bfa677f60419e1b1b` used a one-call
`FLASH`/`NO_LUNA` read-only range contract and returned `PASS/POSITIVE`, no
negative findings, no scope deviation, and no architecture uncertainty. It
confirmed the 17-family registry, immutable planning-only first claim,
fail-closed verifier, canonical test/lint/typecheck integration, and absence of
D1, database, migration, or release artifacts. DeepLuna did not execute the
tests; Sol independently executed and accepted every command above.

## Remaining scientific blockers

- Both formulas remain stale and `QUARANTINED — do not mix or release`.
- Exact builds, lots, finished matrix, substrate, and controlled condition are
  unbound.
- Orris Liquid's carrier is not recorded.
- No trained panel, pilot, power analysis, locked protocol, or confirmatory
  evidence exists.
- No authorized human scientific release has occurred.

These blockers are expected at D0 and prevent experimental or release claims.
They do not invalidate the D0 software gate. D1 is eligible only after this
build-boundary report; it was not started during D0.

The machine-readable companion is
`docs/verification/d0/claim_matrix_gate.json`.
