# Build A Phase A5 implementation plan

Date: 2026-07-30

1. Add failing domain tests for every bottle event, contiguous sequencing,
   idempotency, closed streams, derived dilution, movement replay, lot
   selection, transfer pairing, and typed state deltas.
2. Implement the bottle semantics and pure inventory-operation domain.
3. Add failing model and migration tests for the complete append-only
   inventory movement contract.
4. Implement Alembic revision `20260730_0004`, model fields, constraints,
   deterministic backfill, downgrade, and append-only trigger recreation.
5. Add failing service tests for enriched consumption, reservation/release,
   compensation/reversal, adjustment, close/tare, measured transfer loss,
   stale/idempotent retry, and rollback at injected failure points.
6. Enrich the canonical transaction service and lifecycle state diff without
   introducing another write path.
7. Add active-stream backup/restore replay-equality and end-to-end
   target-to-inventory-to-build-to-bottle tests.
8. Register the new module/tests in the canonical verifier, run focused
   Ruff/MyPy/pytest, then backend and root suites.
9. Run the full canonical verifier, restore protected databases, record the
   A5 exit gate, inspect the diff, and commit only A5 changes.
