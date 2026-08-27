# A2 Slice 4: Canonical lifecycle and versioned API

## Goal

Close the A2 lifecycle and API gate without changing the protected legacy lab
endpoint or schema files. The canonical path must be:

`reservation -> proposal -> human confirmation -> measurement -> atomic bottle
event/inventory movement -> replayed state -> structured diff`.

The same `/api/v1/lab/v2` surface must expose thin operations for analytical
results, sensory results, regulatory assessments, and release reviews by
calling the existing canonical application service.

## Constraints

- Preserve the existing dirty worktree and protected user files.
- Keep handlers thin and return stable domain error codes.
- Keep all execution records append-only and content-hashed.
- Reuse the existing bottle-event and inventory-movement transaction authority.
- Do not create a second measurement truth store.
- Preserve `/api/v1/lab/*` compatibility; add only versioned `/lab/v2` routes.
- Use the existing Alembic chain with one head and reversible SQLite migration.

## TDD sequence

1. Add failing service tests for proposal, confirmation, pre-commit
   measurement, atomic commit, idempotent replay, reservation fulfillment,
   bottle replay, and structured state diff.
2. Add failing API tests for every A2.6 operation that is not already covered.
3. Add failing migration tests for released-schema upgrade, constraints,
   append-only triggers, downgrade/re-upgrade, and representative database copy.
4. Implement the execution models, repository mixin, service mixin, and
   migration.
5. Factor the existing stock-addition write into a transaction-internal helper
   so direct commands and confirmed lifecycle commits share one authority.
6. Add strict lifecycle/science request and response schemas plus a new
   `lab_lifecycle` router, then mount it under the existing `/lab/v2` prefix.
7. Run focused tests, backend tests, root tests, Ruff, mypy, migration head and
   rollback checks, backup/restore checks, canonical verifier, and artifact
   verifier.

## Canonical records

- `LabBottleActionProposal`: immutable physical-action intent bound to one
  active reservation, bottle stream sequence, stock solution, planned mass,
  actor, rationale, idempotency key, and content hash.
- `LabBottleActionConfirmation`: one immutable human decision per proposal.
- `LabBottleMeasurement`: the existing table gains an optional proposal
  reference; exactly one of `proposal_id` and `bottle_event_id` is present.
- `LabBottleActionCommit`: one immutable link from proposal to the atomic bottle
  event, with before/after replay snapshots and structured diff.

## Exit evidence

- All A2.6 operations have versioned routes or already-tested compatible routes.
- Proposal cannot commit without an active reservation, human confirmation, and
  mass measurement.
- Commit is atomic, idempotent, sequence-checked, and fulfills the reservation.
- Replay and diff are deterministic.
- Migration upgrade/downgrade/re-upgrade and representative-copy tests pass.
- The current database and verified backup restore exactly.
- A2 exit report records commands, counts, hashes, skips, and residual risks.
