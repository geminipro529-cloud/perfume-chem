# Build B7 claim authority gate

Status: **PASS**

Recorded: 2026-07-31 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Pre-implementation checkpoint: `0c4b7496dcf71e5ad5d8cd60414086e22beade61`

Verified implementation checkpoint before this report:
`ff1542a02f3564f602ecf7f2ae1e93e4f6e103b9`

## Outcome

Build B7 now converts exact canonical B2-B6 evidence versions into an
append-only, reconstructable, per-claim authority decision. The service does
not accept caller-supplied authority booleans, does not average critical
dimensions, and does not promote an unknown or incomplete support chain.

The decision vocabulary is exactly:

- `ALLOW_EXACT`
- `ALLOW_SCOPED`
- `ADVISORY_ONLY`
- `WITHHOLD_UNKNOWN`
- `BLOCK`

Every persisted decision records the exact claim type and scope, code-owned
policy version and hash, direct upstream version and hash, support links,
decision reason, bounded wording, and authority hash. Reconstruction verifies
those links and hashes rather than trusting the stored decision label.

`release_authority` is always false. B7 does not certify release, legal
compliance, safety, or real-world performance.

## Implemented authority graph

The additive migration `20260731_0011` creates two empty append-only tables:

1. `lab_claim_authority_versions`
2. `lab_claim_authority_support_links`

The supported claim types are:

1. `EXACT_CHEMICAL_IDENTITY`
2. `GRADE_IDENTITY`
3. `PROPERTY_VALUE`
4. `THRESHOLD`
5. `ABOVE_THRESHOLD_SCREENING`
6. `ANALYTICAL_IDENTIFICATION`
7. `ANALYTICAL_QUANTITATION`
8. `NATURAL_CONSTITUENT_PROFILE`
9. `KNOWLEDGE_RULE_RECOMMENDATION`
10. `REGULATORY_SCREENING`
11. `FORMULA_OR_MODEL_COMPARISON`

Support links use the roles `SUPPORTING`, `CONTRADICTING`, and `LIMITATION`
and the kinds `PROPERTY_ASSERTION`, `OAV_ASSESSMENT`, `KNOWLEDGE_RULE`,
`ANALYTICAL_ASSESSMENT`, `COMPOSITION_PROFILE`, and
`REGULATORY_SNAPSHOT`.

The service:

- resolves typed canonical B2-B6 support rather than generic row IDs;
- ignores caller authority booleans and applies deterministic code-owned
  policies;
- requires exact claim scope and exact version IDs;
- blocks or withholds when a required upstream dimension is contradictory,
  speculative, unknown, stale, incomplete, or missing;
- preserves limitations as explicit support links;
- requires a `COMPLETE` authoritative natural profile before scoped
  promotion;
- enforces scoped revision lineage through the latest B7 parent and latest A2
  chain while keeping claim scope immutable;
- hashes the policy, direct upstream evidence, links, and final authority row;
  and
- reconstructs and verifies every hash and lineage edge.

## Defects found and closed

The first implementation treated a `PARTIAL` natural composition profile as
authoritative and could issue `ALLOW_SCOPED`. A focused negative test
reproduced the defect; the service now requires profile completeness
`COMPLETE`.

The first DeepLuna final audit found three residual test-coverage gaps:
speculative/unknown evidence, `LIMITATION` support, and missing required
fields at the integration boundary. Those paths were reproduced locally,
covered with negative tests, and included in the final 58-test and 324-test
runs. A second bounded DeepLuna Fast audit reported `PASS` with no residual
risks.

## Verification evidence

Supported runtime:

- Python `3.11.15`
- Node `v26.3.0`
- Alembic head `20260731_0011`

Exact B7 gate:

```powershell
python -m pytest tests/unit/test_b7_claim_authority_schema.py tests/unit/test_b7_claim_authority_service.py tests/integration/test_b7_claim_authority_migration.py tests/integration/test_b7_claim_authority_e2e.py --color=no -q --basetemp=../output/pytest-temp-backend/b7-exact-final
```

Final result: `58 passed in 61.58s`, exit `0`.

Captured streams:

- `logs/pytest_b7.stdout.txt`
- `logs/pytest_b7.stderr.txt`

A2 through B7 compatibility, migration, and backup/restore gate:

```powershell
python -m pytest <A2 and B1-B7 schema/service/migration/e2e suites> tests/integration/test_lab_migration.py tests/integration/test_backup_restore.py --color=no -q --basetemp=../output/pytest-temp-backend/b7-compat-final
```

Final-state result: `324 passed in 308.91s`, exit `0`.

The first compatibility run produced `317 passed, 3 failed`; all three
failures were stale `CURRENT_HEAD` expectations for `20260731_0010` in the
canonical migration and backup/restore tests. After advancing those constants
to `20260731_0011`, the three focused cases passed and the then-current full
suite passed `320` tests. The additional post-audit negative tests increased
the final complete suite to `324`, all passing.

Static gates:

```powershell
python -m ruff check <B7 models/repository/service/migration/tests and shared registrations> --no-cache --no-fix --output-format concise
python -B -m mypy app/models/lab_claims.py app/repositories/lab_claims.py app/services/lab_claims.py --ignore-missing-imports --no-color-output --no-pretty --cache-dir=../output/mypy-cache-b7-final
```

Results:

- Ruff: `All checks passed!`, exit `0`
- mypy: `Success: no issues found in 3 source files`, exit `0`

Migration and recovery assertions covered by executable tests include:

- prior-head to B7 upgrade with zero backfill and no reinterpretation;
- both empty B7 tables and current head;
- downgrade and re-upgrade;
- foreign keys, uniqueness, check constraints, and SQLite append-only guards;
- exact typed support and direct-upstream hash verification;
- revision lineage and scope immutability;
- database integrity; and
- backup creation, validation, staged restore, activation, and replay.

## Pre-write recovery archive

Restorable path-preserving archive:

`D:\.backups\perfume-chem\build-b7-prewrite-20260731T064410+0700.tar`

- bytes: `97275904`
- SHA-256:
  `2d487c8b1b681eccc267bb2957d1e6ad03f62621801773a612188165256397dd`
- `405` archived files restored and re-hashed successfully
- `407` archive entries including the manifest and absent-planned-path list
- preserves `397` pre-existing non-runtime dirty/untracked files
- excludes only live scheduler/runtime state under `.deepluna-home/` and
  `.cheapluna-home/`

The archive is a verified backup, not merely a file-hash inventory.

## Protected database proof

Before and after implementation and verification:

| Path | Bytes | SHA-256 | Integrity |
|---|---:|---|---|
| `perfume_chem.db` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | unchanged empty placeholder; not opened for migration |
| `data/perfumery_kb.db` | 2084864 | `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1` | main database unchanged; read-only `PRAGMA quick_check`: `ok` |

No migration or verifier was run against either protected database. The
read-only SQLite integrity check touched the existing untracked SHM runtime
sidecar timestamp; it did not change the main database content hash.

## DeepLuna use

Fresh exact-project checks returned `READY`, runtime `CANDIDATE_V2`, release
`0.9.9`, with zero active reads/writes, zero queue, zero open reservation, and
provider calls enabled.

A bounded pre-implementation FLASH/`NO_LUNA` gap audit passed:

- job: `DS-f4ac6cf7f5dce29740ee81de03b42135`
- result: `PASS`

The first final static audit passed the implementation but identified the
three negative-path coverage gaps recorded above:

- job: `DS-da6d3036641b2403b402da06803018b5`

After local reproduction and closure, a fresh exact-project check preceded a
second bounded DeepLuna Fast call using
`deepseek-ai/DeepSeek-V4-Flash` through the FLASH route with `NO_LUNA`, one
attempt, and no fallback:

- job: `DS-e4aa7a0fa84b0e7e7a9d2b40fab75eb4`
- provider calls: `1`
- prompt tokens: `72815`
- completion tokens: `854`
- total tokens: `73669`
- measured spend delta: `$0.010060605`
- result: `PASS`
- residual risks: none
- scope deviation: false

DeepLuna remained advisory. Sol independently reran the exact 58-test gate,
the complete 324-test compatibility gate, Ruff, mypy, migration-head,
archive-restoration, and protected-database checks before acceptance.

## Captured log digests

| Log | Bytes | SHA-256 |
|---|---:|---|
| `alembic_heads.stdout.txt` | 22 | `056bb79603dcf2ec03672d61437ea4ff2cbdfe128097789a98b87afbb08e68fd` |
| `deepluna_gap_audit.json` | 9040 | `4cbc03905a16b7b1f43ed27266c586676c11abf5de74c6802ade2927268c72db` |
| `deepluna_final_audit_initial.json` | 8585 | `345cbeb25d088f42e6d95c5896243718e8932c45297a57c2abaf0cfe2f11ca14` |
| `deepluna_final_audit_pass.json` | 7851 | `dd0b8f6be90c189dad3f54a85dd79dc5f412b8513a65e38f6ae69c70ad80f7d4` |
| `mypy.stdout.txt` | 44 | `281a094c39385b4d7b53e5db635f52158036861433c2a4975b9039e77a627a24` |
| `protected_database_hashes.json` | 519 | `6f312561fad403819b3ac9e47d6fb5ad4bd901d75bf186ffce7382e0f39c046a` |
| `protected_kb_quick_check.stdout.txt` | 4 | `9f2a59a60e65fbcd5a3e1b7248adf92890ce3a32b19e43fb4751c2657196de13` |
| `pytest_b7.stdout.txt` | 112 | `2ac3c628abb3ed7757eea58881cd2c09d1028df8832e0a241750d8870b02bd54` |
| `pytest_compat.stdout.txt` | 438 | `cfe78d4d0475f85ae077d8f4b45ed66c337da3be9286a0485fbbe29c740a3e03` |
| `recovery_archive_check.json` | 299 | `bc0c590677594fd7cd8a636f7e802730c4ee4014628e35ef0b704e828bbedd54` |
| `ruff.stdout.txt` | 20 | `a4443afdcfb6d7363adb285762515ccf7cf50473b1a05c20c1a50f6bed4d26b0` |

Every captured stderr file is empty and has the empty-file SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Residual limits and gate state

- B7 evaluates only explicit canonical version IDs and exact immutable claim
  scopes; it does not infer missing evidence.
- B7 is not release authority, legal advice, a safety certificate, or evidence
  of real-world performance.
- Production API/UI routing is outside B7.
- Unrelated tracked and untracked work remains outside B7 staging scope and
  is preserved.

The Build B7 exit gate passes. This permits B8 planning, but does not imply
that Build B or the complete A-D program is finished.
