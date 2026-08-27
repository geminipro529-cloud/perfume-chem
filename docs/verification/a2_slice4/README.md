# A2 Slice 4 verification: lifecycle and versioned API

## Scope

This slice closes the canonical A2 physical execution lifecycle and the missing
versioned API operations. It preserves the existing `/api/v1/lab/*`
compatibility surface and adds only `/api/v1/lab/v2/*` routes.

The canonical execution path is:

```text
active reservation
-> immutable action proposal
-> immutable human confirmation
-> immutable gravimetric measurement
-> atomic bottle event + inventory movement
-> fulfilled reservation
-> replayed bottle state
-> stored structured state diff
```

## Implementation

Canonical records:

- `LabBottleActionProposal`
- `LabBottleActionConfirmation`
- `LabBottleMeasurement` with exactly one proposal or bottle-event authority
- `LabBottleActionCommit`

The existing stock-addition operation now delegates to one
transaction-internal implementation. Confirmed lifecycle commits call the same
implementation inside the canonical transaction, then append reservation
fulfillment and before/after/diff evidence.

The `lab-export-v4` contract includes planning, science, proposal,
confirmation, measurement, and commit records in foreign-key-safe order.
`lab-export-v1`, `v2`, and `v3` remain supported and do not expose
proposal-bound measurements.

Versioned routes expose:

- action proposal, confirmation, measurement, and commit;
- bottle replay and action state diff;
- analytical result;
- sensory result;
- regulatory assessment;
- release review.

All route handlers delegate to `LabService` and return stable coded errors.

## Migration evidence

Alembic has one head:

```text
20260730_0003 (head)
```

The execution migration:

- upgrades a `20260730_0002` representative database copy;
- preserves legacy event-bound bottle measurements;
- installs append-only triggers and database constraints;
- downgrades to `20260730_0002`;
- re-upgrades to `20260730_0003`;
- fails closed when a downgrade cannot map an uncommitted proposal
  measurement.

Focused migration result:

```text
17 passed
```

## Test and static-analysis evidence

Focused lifecycle/export/API/transaction result:

```text
24 passed
```

Focused final lifecycle/API result after the error-wrapper correction:

```text
4 passed
```

Full backend:

```text
272 passed
```

Supported root suite:

```text
1000 passed
```

Bare root `pytest` was rejected as evidence because it traversed a preserved
ACL-protected archive. The supported `pytest -q tests` scope passed. No archive
was changed or cleaned.

Ruff:

```text
All checks passed
```

Mypy:

```text
Success: no issues found in 86 source files
```

The non-ignored full-app mypy probe reported only absent optional dependency
stubs/imports for `jose`, `passlib`, `llama_cpp`, `torch`, and `transformers`;
the repository verifier's accepted `--ignore-missing-imports` gate passed.

## Canonical verifier and artifacts

Final exact-state canonical verifier:

```text
19 required checks passed
0 required checks failed
2 optional Docker checks skipped
completion_gate=PASS_WITH_SKIPS
```

`verification_runs/project_verification.json` SHA-256:

```text
f3d7720c6085c5614c320eed1b9e9185346d5114518a72cdde80879c9735a382
```

Golden fixture lock:

```text
0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec
```

Artifact verifier:

```text
status=WARN
blocking=0
NONE=452
QUARANTINED=14
UNBOUND_LEGACY=49
```

Quarantined and unbound legacy artifacts remain non-promoting.

## DeepLuna bounded audit

Final read-only invariant audit:

```text
job=DS-7e960aabcebe3e0e476b75d47438c216
status=PASS
evidence_verdict=POSITIVE
negative_findings=0
scope_deviation=false
```

Sol independently verified the implementation and executable tests. Provider
output did not establish acceptance.

## Protected state

- `perfume_chem.db`: zero bytes, SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `data/perfumery_kb.db`: restored after verifier execution, SQLite integrity
  `ok`, SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`
- Existing tracked and untracked user work remains preserved.

## Residual boundary

Laboratory Beta software verification is ready. Scientific release remains
blocked by missing held-out sensory validation; this slice does not promote a
formula or scientific claim.
