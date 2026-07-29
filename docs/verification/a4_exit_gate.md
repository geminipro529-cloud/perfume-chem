# Build A Phase A4 exit gate

Date: 2026-07-30

Status: PASS for the local authority and claim-gating software boundary. This
does not grant scientific or product release authority.

## Implemented boundary

- `engine/authority_gates.py` defines the canonical actor types, action states,
  operating modes, mode/action permissions, claim axes, claim decisions,
  regulatory decisions, and stable denial reasons.
- Mode permissions are explicit for all eleven required operating modes.
  Reconstruction cannot perform a live batch commit; live-batch mode can.
- Claim authority is evaluated independently for exact mass balance,
  identity, active concentration, above-threshold likelihood, sensory
  intensity, target similarity, family preservation, regulatory screening,
  and release. No averaged score can promote one unsupported axis through
  strength on another axis.
- Family, concentration/density, and regulatory gates return typed decisions
  and stable reasons. Unknown or inapplicable evidence cannot silently become
  a pass.
- The release pipeline delegates mode protection to the canonical authority
  evaluator.
- `a4-claim-v1` service writes compute the maximum permitted claim decision,
  reject overclaims with `CLAIM_DECISION_EXCEEDS_AUTHORITY`, and persist the
  computed gate result. The legacy `a2-claim-v1` behavior remains readable and
  unchanged.

## Negative-test evidence

The A4 tests prove that unsupported identity, quantity/concentration, family,
safety/regulatory, sensory, analytical, and release claims are blocked or
withheld with stable reasons. They also cover actor/action transitions,
complete mode allowlists, conflict and review requirements, and prevention of
decision overclaiming.

Focused verification passed:

- canonical authority tests: 28 passed;
- authority plus pipeline tests: 46 passed;
- focused A4 service tests: 2 passed;
- complete A2/A4 science-service test module: 10 passed;
- backend Ruff: passed;
- backend MyPy: 86 source files passed;
- engine verifier Ruff and MyPy surfaces: passed.

## Canonical verifier

The full verifier report at
`verification_runs/a4-project-verification.json` recorded:

- engine truth-core shard: 188 passed;
- engine data/knowledge shard: 225 passed;
- engine gates/families shard: 561 passed;
- engine legacy shard: 68 passed;
- backend suite: 277 passed;
- 19 required checks passed;
- zero failures;
- optional Docker build and smoke checks skipped because Docker was not
  requested;
- completion gate `PASS_WITH_SKIPS`;
- report SHA-256
  `ab8e79f3e92f58a51d49ecdc6856368040728b2798c91f15208c6daf17490157`.

## Protected database state

After verification, `data/perfumery_kb.db` was restored from the previously
verified path-preserving recovery candidate:

- SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- SQLite `PRAGMA integrity_check`: `ok`.

The protected canonical `perfume_chem.db` remained zero bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Exit decision

All A4 exit conditions pass for the local software boundary. Unsupported
authority claims fail closed, reasons are stable, and the canonical verifier
passes. Scientific release remains blocked until the later evidence gates are
satisfied.
