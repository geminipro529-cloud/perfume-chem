# Build A Phase A2 authoritative re-verification plan

Date: 2026-08-02

Starting checkpoint: `9f14fe923625a076030e5253b0d35a8b1a108efa`

## Authority and baseline

- Authority is the current repository, A0 ADR, A2 master requirements,
  executable tests, Alembic chain, and canonical verifier.
- The tracked A2 exit report is historical evidence only. Its 1,000/272 test
  counts and `20260730_0003` head statement are stale.
- Fresh A2 baseline: 82 tests passed across all 19 `test_a2_*.py` files using
  the repository Poetry environment. JUnit SHA-256:
  `ba0597fbe4d59765636f29639102a13a4afd3d31d7f004c27aa6e2c28503c280`.
- Fresh Alembic inventory: one head, `20260731_0012`.
- Fresh full verifier inherited from the A1 checkpoint: 19 required checks
  passed, 0 failed, with two declared Docker skips; 1,095 engine and 629
  backend tests passed.

## Reproduced gap

`backend/app/api/v1/endpoints/lab.py::add_material_alias` still constructs a
`LabMaterialAlias` and directly calls `session.add`, `session.commit`, and
`session.refresh`. This is the exact exception named by the A0 ADR and violates
the canonical endpoint -> `LabService` -> `LabRepository` transaction chain.
The compatibility test proves alias creation and resolution but does not prove
service routing.

DeepLuna Fast job `DS-8b881df2226af08f61df46bd57d38317` mechanically
confirmed the same bounded discrepancy. Sol independently verified the whole
service and repository files contain no canonical alias-write method.

## Recovery package

- Archive:
  `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\work\a2_preedit_20260802_035345.tar`
- SHA-256:
  `9f1cd8f613832426b773496779fce6ee1bf889ead608577f688f03ae6527398e`
- Contents: five path-preserved affected files.
- Restore verification: five files, zero length or SHA-256 mismatches.

## TDD implementation sequence

1. Strengthen the A2 write-path guard so endpoint-owned `add`, `flush`,
   `commit`, `refresh`, or `rollback` calls fail closed. Prove RED against the
   current alias endpoint.
2. Add `LabService.create_material_alias`, validating nonempty alias text,
   checking material existence, entering `_transaction`, and persisting via
   `LabRepository.add`.
3. Route the existing v1 endpoint through `_service_call` and the new service
   method. Preserve its URL, status, payload, and alias-resolution behavior.
4. Run focused guard and Phase 1A material tests, then all 19 A2 files, backend
   lint/typecheck, migration-head check, and the canonical full verifier.
5. Replace stale A2 exit evidence with current counts, hashes, migration state,
   the exact before/after disposition, and final bounded Fast validation.
6. Commit only the A2 delta and evidence after every exit condition passes.

No new schema or migration is needed. No existing immutable planning or
lifecycle model is redesigned.
