# Build B6 regulatory authority gate

Status: **PASS**

Recorded: 2026-07-31 (Asia/Bangkok)

Branch: `codex/add-inventory-materials`

Pre-implementation checkpoint: `ddea825e9e5478c124ffa7c8098c44a49b45a035`

## Outcome

Build B6 now has an append-only, dated, jurisdiction- and use-scoped
regulatory screening authority. It persists exact official-source versions,
rule versions, supplier-document bindings, natural/trade composition
profiles, immutable snapshots, and per-rule findings.

The result vocabulary is exactly:

- `PASS_FOR_DECLARED_SCOPE`
- `FAIL`
- `UNKNOWN`
- `NOT_EVALUATED`

Only `PASS_FOR_DECLARED_SCOPE` receives service-generated scoped screening
wording. The wording deliberately makes no certificate or legal-conformity
claim. Legacy A2 `PASS` rows remain historical context and do not become B6
authority without a linked passing B6 snapshot.

This is a regulatory screening authority, not legal advice, an IFRA
certificate, or a legal certificate.

## Implemented authority graph

The additive migration `20260731_0010` creates seven empty append-only tables:

1. `lab_regulatory_source_versions`
2. `lab_regulatory_rule_versions`
3. `lab_supplier_document_bindings`
4. `lab_regulatory_composition_profiles`
5. `lab_regulatory_composition_entries`
6. `lab_regulatory_snapshot_versions`
7. `lab_regulatory_authority_findings`

The service:

- requires same-UTC-date current-source checks;
- keeps draft, consultation, watchlist, superseded, and not-yet-applicable
  rules non-enforced;
- handles action-specific inclusive placement and availability transition
  boundaries;
- binds supplier documents to exact supplier, product, code, grade, version,
  and lot scope;
- requires current SDS, IFRA-certificate, and allergen-declaration bindings
  for every evaluated stock;
- aggregates formula active fractions from requested mass and exact stock
  active fraction;
- aggregates build plans from immutable planned active/raw quantities;
- uses only `REGULATORY` natural/trade composition entries;
- turns missing, partial, stale, or unknown natural composition into
  `UNKNOWN`;
- preserves a known over-limit failure even when other composition is
  unknown;
- applies declaration thresholds to exact declared wording; and
- persists the snapshot and every finding atomically.

## Current-source verification

Official sources were rechecked on 2026-07-31:

- IFRA's official consultation update says the 52nd Amendment consultation
  closed on 2026-06-12 and formal notification was expected near the end of
  November 2026. B6 therefore records it as `CONSULTATION`, not enforced:
  <https://ifrafragrance.org/latest-updates/ifra-news/ifra-52nd-amendment-consultation-closed>
- Commission Regulation (EU) 2023/1545 provides 0.001% leave-on and 0.01%
  rinse-off declaration thresholds, with inclusive non-compliant placement
  and availability transition ends on 2026-07-31 and 2028-07-31:
  <https://eur-lex.europa.eu/eli/reg/2023/1545/oj/eng>

These live observations are not silently reused: an evaluation requires
registered source rows checked on the same UTC date.

## Verification evidence

Supported runtime:

- Python `3.11.15`
- Node `v26.3.0`
- Alembic head `20260731_0010`

Exact B6 gate:

```powershell
python -m pytest tests/unit/test_b6_regulatory_schema.py tests/unit/test_b6_regulatory_service.py tests/integration/test_b6_regulatory_migration.py tests/integration/test_b6_regulatory_e2e.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-exact-final-1
```

Post-audit result: `30 passed in 42.72s`, exit `0`.

Captured streams:

- `logs/pytest_b6.stdout.txt`
- `logs/pytest_b6.stderr.txt`

B1–B6 compatibility and operational migration/backup gate:

```powershell
python -m pytest tests/unit/test_a2_science_schema.py tests/unit/test_a2_science_service.py tests/integration/test_a2_science_migration.py tests/unit/test_b1_source_schema.py tests/unit/test_b1_source_service.py tests/integration/test_b1_source_migration.py tests/unit/test_b2_property_schema.py tests/unit/test_b2_property_service.py tests/integration/test_b2_property_migration.py tests/unit/test_b3_threshold_schema.py tests/unit/test_b3_threshold_service.py tests/integration/test_b3_threshold_migration.py tests/unit/test_b4_rule_schema.py tests/unit/test_b4_rule_service.py tests/integration/test_b4_rule_migration.py tests/unit/test_b5_analytical_schema.py tests/unit/test_b5_analytical_service.py tests/integration/test_b5_analytical_migration.py tests/integration/test_b5_analytical_e2e.py tests/unit/test_b6_regulatory_schema.py tests/unit/test_b6_regulatory_service.py tests/integration/test_b6_regulatory_migration.py tests/integration/test_b6_regulatory_e2e.py tests/integration/test_lab_migration.py tests/integration/test_backup_restore.py --color=no -q --basetemp=../output/pytest-temp-backend/b6-compat-final-1
```

Post-audit result: `266 passed in 239.16s`, exit `0`.

The first compatibility run produced `263 passed, 3 failed`; all failures were
reproduced as stale test constants that still expected B5 head
`20260731_0009`. Updating the two canonical `CURRENT_HEAD` declarations to
`20260731_0010` made the three focused failures pass, after which the complete
266-test command passed.

Static gates:

```powershell
python -m ruff check <B6 model/repository/service/migration/tests and shared registrations> --no-cache --no-fix --output-format concise
python -B -m mypy app/models/lab_regulatory.py app/repositories/lab_regulatory.py app/services/lab_regulatory.py --ignore-missing-imports --no-color-output --no-pretty --cache-dir=../output/mypy-cache-b6-final
```

Results:

- Ruff: `All checks passed!`, exit `0`
- mypy: `Success: no issues found in 3 source files`, exit `0`

Migration and recovery assertions covered by executable tests include:

- prior-head to B6 upgrade without prior-row reinterpretation;
- seven empty B6 tables;
- current head;
- downgrade and re-upgrade;
- foreign keys, uniqueness, check constraints, and SQLite append-only guards;
- database integrity; and
- backup creation, validation, staged restore, activation, and replay.

## Pre-write recovery archive

Restorable path-preserving archive:

`D:\.backups\perfume-chem\build-b6-prewrite-20260731T052656+0700.tar`

- bytes: `102200320`
- SHA-256:
  `67742cc6f30a979811df359675e108af0cc6cdb0d1f571cf29d89faad61e6bbf`
- verified by extraction and re-hashing `455` archived files
- includes all `452` non-runtime dirty/untracked paths plus three shared B6
  target files
- excludes only the live `.deepluna-home/` scheduler runtime

The earlier 28,113-byte partial `.tar.gz` is explicitly not a valid backup and
is not used as evidence.

## Protected database proof

Before and after implementation/verification:

| Path | Bytes | SHA-256 | Integrity |
|---|---:|---|---|
| `perfume_chem.db` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | unchanged empty placeholder; not opened for migration |
| `data/perfumery_kb.db` | 2084864 | `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1` | read-only `PRAGMA quick_check`: `ok` |

No migration or verifier was run against either protected database.

## DeepLuna use

A fresh exact-project check returned `READY`, runtime `CANDIDATE_V2`, release
`0.9.9`, with zero active reads/writes, zero queue, zero open reservation, and
provider calls enabled. A bounded pre-implementation FLASH/`NO_LUNA` gap audit
was used as advisory evidence; Sol reproduced its repository claims locally
and retained final architecture, provenance, safety, and acceptance authority.

A final fresh exact-project check again returned `READY`. One bounded
DeepLuna Fast call used
`deepseek-ai/DeepSeek-V4-Flash` through the FLASH route with `NO_LUNA`, one
attempt, and no fallback:

- job: `DS-e8a76a9cb4582878df4b0aab4448d3ab`
- provider calls: `1`
- prompt tokens: `78488`
- completion tokens: `746`
- total tokens: `79234`
- measured spend delta: `$0.0107973`
- result: `PASS`
- negative findings: none
- scope deviation: false

The audit found no correctness, fail-closed, or report defects and recommended
local reproduction. Sol then reran the exact 30-test B6 gate and complete
266-test compatibility gate; both passed with the post-audit results recorded
above. DeepLuna remained advisory and did not make the acceptance decision.

## Captured log digests

| Log | Bytes | SHA-256 |
|---|---:|---|
| `alembic_heads.stdout.txt` | 22 | `82e7a1b9031ef8fde0c8b3cdb61f7b67aed0dd8e1e31fbd9f6aa702057102907` |
| `mypy.stdout.txt` | 44 | `281a094c39385b4d7b53e5db635f52158036861433c2a4975b9039e77a627a24` |
| `pytest_b6.stdout.txt` | 102 | `2bc1142e4df69850a32f2b4e1ce16d9bbfb63a8a759cc9512dc3ed750e437413` |
| `pytest_compat.stdout.txt` | 357 | `d4b7e6a50383f1f8b5f4287abf769e77a9f46304e1928536c7448bab45538666` |
| `ruff.stdout.txt` | 20 | `a4443afdcfb6d7363adb285762515ccf7cf50473b1a05c20c1a50f6bed4d26b0` |
| `protected_kb_quick_check.stdout.txt` | 4 | `9f2a59a60e65fbcd5a3e1b7248adf92890ce3a32b19e43fb4751c2657196de13` |

Every captured stderr file is empty and has the empty-file SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Residual limits and gate state

- B6 operates only on explicitly registered exact source, rule, supplier, and
  composition versions. It does not infer missing compliance data.
- Source-currentness is a dated observation and must be refreshed for a later
  evaluation date.
- B6 does not add production API/UI routing; that remains a later phase.
- Unrelated tracked and untracked work remains present and is outside B6
  staging scope.
- Full-worktree `git diff --check` reports two pre-existing unrelated trailing
  blank-line issues under `future_modules/`; B6 exact paths pass the scoped
  whitespace gate.
- Exact-path commits and final empty-index/protected-state checks are performed
  as the gate package is recorded; unrelated tracked and untracked work is
  preserved.
