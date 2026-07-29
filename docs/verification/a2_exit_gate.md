# Build A A2 exit gate

Status: **PASS**

## Gate decisions

| Requirement | Result | Evidence |
|---|---:|---|
| One persisted truth representation per domain | PASS | Canonical SQLAlchemy planning, execution, analytical, sensory observation, regulatory, and claim-authority records; legacy writers are prohibited or compatibility-only canonical writers. |
| Canonical immutable build plans | PASS | Versioned hash-chained build-plan records and database append-only guards. |
| Target and build are independent | PASS | Accepted target, inventory mapping, and build-plan references are distinct persisted versions. |
| No dual writes | PASS | Legacy ledgers are read-only adapters; physical execution writes the canonical bottle event/inventory movement transaction. |
| Migration and rollback | PASS | One `20260730_0003` head; released-copy upgrade, downgrade, re-upgrade, constraints, append-only guards, and backup/restore tests pass. |
| API compatibility/versioning | PASS | Existing `/api/v1/lab/*` remains; canonical additions are under `/api/v1/lab/v2/*`. |
| Target-to-inventory-to-build integration | PASS | Versioned planning API integration and lifecycle execution tests pass. |
| All engine/backend/verifier checks | PASS | 1,000 root tests, 272 backend tests, Ruff, mypy, package/wheel smoke, and 19 canonical required checks pass. |

## A2.6 operation coverage

| Operation | Versioned authority |
|---|---|
| Target hypothesis creation | `POST /api/v1/lab/v2/targets` |
| Target acceptance | `POST /api/v1/lab/v2/targets/{id}/accept` |
| Inventory mapping | `POST /api/v1/lab/v2/inventory-mappings` |
| Build-plan draft/review/approval | `POST /api/v1/lab/v2/build-plans` and transitions |
| Stock reservation | `POST /api/v1/lab/v2/reservations` |
| Physical-action proposal | `POST /api/v1/lab/v2/actions` |
| Human confirmation | `POST /api/v1/lab/v2/actions/{id}/confirmations` |
| Measurement recording | `POST /api/v1/lab/v2/actions/{id}/measurements` |
| Transaction commit | `POST /api/v1/lab/v2/actions/{id}/commit` |
| Bottle replay | `GET /api/v1/lab/v2/bottles/{id}/replay` |
| Structured state diff | `GET /api/v1/lab/v2/actions/{id}/diff` |
| Analytical result | `POST /api/v1/lab/v2/analytical-results` |
| Sensory result | `POST /api/v1/lab/v2/sensory-results` |
| Regulatory assessment | `POST /api/v1/lab/v2/regulatory-assessments` |
| Release review | `POST /api/v1/lab/v2/release-reviews` |

## Evidence pointers

- `docs/verification/a2_slice1/README.md`
- `docs/verification/a2_slice2/README.md`
- `docs/verification/a2_slice3/README.md`
- `docs/verification/a2_slice4/README.md`
- `verification_runs/project_verification.json`

## Non-promotion statement

This gate accepts A2 canonical convergence only. It does not claim held-out
sensory validation, calibrated headspace performance, regulatory universality,
commercial readiness, or scientific release.
