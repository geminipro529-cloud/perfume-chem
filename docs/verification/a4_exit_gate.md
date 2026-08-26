# Build A Phase A4 exit gate

Date: 2026-08-02

Authoritative source baseline:
`f979461ccf7f6290541c0bf5b27e59eb22fd4d4a`.

Status: PASS for the local authority and claim-gating software boundary. This
does not grant scientific or product release authority.

## Reverification method

The 2026-07-30 report was independently checked against the live tree. Its
verifier counts and protected root-database description were stale. Before
replacement, it was preserved in the path-restorable archive
`a4_prereport_20260802_044827.tar`, SHA-256
`ca1d213d5153a1bb82f1a43a426b287bde6d43d4425ffe15f79a50b9f67f12ed`.
An extracted copy matched the original report SHA-256 exactly.

No production source, migration, database, or release artifact was changed by
this reverification.

## Implemented boundary

- `engine/authority_gates.py` defines the six canonical actor types, eight
  action states, eleven operating modes, explicit mode/action allowlists,
  transition permissions, nine independent claim axes, decision states,
  regulatory states, and stable denial reasons.
- Transition evaluation accounts for record state, requested state, actor,
  mode-sensitive AI release prevention, evidence, safety, and human
  confirmation. AI cannot self-release or confirm physical execution.
- Reconstruction cannot perform a live-batch atomic commit; live-batch mode
  can. Cross-mode target rewrite, formula mutation, and certification actions
  are absent from every permissive allowlist.
- Exact mass balance, identity, active concentration, above-threshold
  likelihood, sensory intensity, target similarity, family preservation,
  regulatory screening, and release are evaluated independently. No average
  can promote an unsupported dimension.
- Undefined family yields `WITHHOLD_UNKNOWN` for family-specific evaluation.
  Family drift and genre shift block only when defined evidence supports those
  findings.
- Concentration requires its actual basis, active fraction, and density only
  when density is required. Carrier presence alone does not block.
- Regulatory `PASS_FOR_DECLARED_SCOPE` requires an effective standard, complete
  dated scope fields and source digest, no violation, and no unresolved item.
- The release pipeline delegates mode protection to the canonical evaluator.
  `a4-claim-v1` service writes compute maximum authority, persist the gate
  result, and reject overclaims with
  `CLAIM_DECISION_EXCEEDS_AUTHORITY`; legacy reads remain unchanged.

## Fresh local evidence

- `tests/test_authority_gates.py` plus `tests/test_pipeline_gates.py`: 46
  passed; JUnit SHA-256
  `f87c4c157162ffead61ab5e6b8b5dcfc8e897f58531ec989533fc1cf424c3d1e`.
- Complete `backend/tests/unit/test_a2_science_service.py`: 10 passed; JUnit
  SHA-256
  `80b9b7783adef4d2ca26ea667be90869735dafd5184be98aff2155571cb3f598`.
- Focused engine and backend Ruff checks: passed.
- Focused MyPy checks for `engine/authority_gates.py` and
  `backend/app/services/lab_science.py`: passed with no issues.

The negative tests cover unsupported identity, quantity/concentration,
family, safety/regulatory, sensory, analytical, and release claims; transition
authorization; all eleven mode allowlists; contradictions; review and
confirmation; and persistence overclaim rejection.

## Canonical verifier

The latest full current-tree verifier at
`verification_runs/project_verification.json` records engine 1,095 tests,
backend 630 tests, 1,725 combined tests, 19 passed required checks, zero failed
or omitted checks, and two optional Docker skips because Docker was not
requested. Completion gate is `PASS_WITH_SKIPS`; report SHA-256 is
`52491a72415ba34881d13c212269325add6b183b56e74071f4f08e58ebb4e95a`.

## Protected database state

Both databases remained byte-identical across the focused A4 checks and passed
read-only SQLite `PRAGMA quick_check`:

- `data/perfumery_kb.db`: 2,084,864 bytes, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- `perfume_chem.db`: 12,288 bytes, SHA-256
  `02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`.

The latter contains only an empty `alembic_version` table. This observation is
not migration authority; the independent Alembic single-head gate remains
authoritative.

## DeepLuna Fast audit

One malformed range packet was rejected locally before provider execution and
is not evidence. A corrected fresh exact-project check returned `READY` for
`project_id=perfume-chem`, runtime `CANDIDATE_V2`, server 0.9.9, with no active,
queued, open-reserved, or unknown-reserved work.

Bounded read-only Fast job `DS-b08694e644b1ea8f20e952644dbd1863`
used route `FLASH` with `NO_LUNA` and one allowed provider call. It returned
`PASS`, execution status `ACCEPTED`, and evidence verdict `POSITIVE`, with no
negative findings, residual risks, scope deviation, contradiction, or
acceptance-blocking gap. DeepLuna supplied review evidence only; Sol retained
final authority.

## Exit decision

All A4 exit conditions pass for the local software boundary. Unsupported
identity, quantity, family, safety, sensory, analytical, and release claims
fail closed with stable reasons; overclaims cannot be persisted; and the
repository verifier passes. Scientific release remains blocked until later
experimental evidence gates are satisfied.
