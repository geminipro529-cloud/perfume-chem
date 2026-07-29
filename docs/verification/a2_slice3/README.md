# A2 Slice 3 Verification Evidence

Status: `A2_SLICE3_PASS`

Starting implementation commit:
`174925a`

Predecessor implementation commit:
`95380e440318994c6eed23ac2144143569f169fe`

## Implemented boundary

- Added pure canonical/legacy adapters for stock, bottle replay, formula DAG,
  analytical data, sensory experiments, regulatory snapshots, evidence import,
  and analytical import.
- Added deterministic non-persisting import drafts with canonical JSON hashes.
- Made duplicate legacy ledgers fail closed on public mutation.
- Added read-only hydration constructors that do not call deprecated mutators.
- Added an AST-based dual-write regression guard.
- Added adapter, equivalence, write-closure, and guard tests.
- Added the new analytical/evidence/sensory production modules to canonical
  engine lint and type-check coverage.
- Deleted no legacy table or source file.
- Created no migration and did not initialize the zero-byte canonical
  database.

## TDD evidence

The first supported-runtime attempt was invalid because the disposable Python
3.11 verifier environment lacked the backend pytest-asyncio dependency. The
environment was corrected to repository-compatible pytest 7.4 and
pytest-asyncio 0.21.

The unchanged write-closure test then produced the intended RED result:

```text
ImportError: cannot import name 'LegacyWriteProhibitedError'
```

After implementation:

```text
backend/tests/unit/test_a2_legacy_write_closure.py
2 passed
```

Focused adapter, guard, and affected historical calculations:

```text
140 passed
```

## Verification evidence

Supported runtime:

```text
Python 3.11.15
pytest 7.4.4
pytest-asyncio 0.21.2
```

Backend suite:

```text
261 passed in 152.27s
```

Root suite:

```text
1000 passed in 107.31s
```

Backend type check:

```text
Success: no issues found in 81 source files
```

Focused engine type check:

```text
Success: no issues found in 7 source files
```

Focused production/test lint:

```text
All checks passed
```

Canonical full verifier:

```text
19 required checks passed
0 required checks failed
2 optional Docker checks skipped
completion_gate=PASS_WITH_SKIPS
```

The verifier's golden fixture hash remained unchanged:

```text
0067d16228bb18636518236795b00a368c02e7a3195ea5ce184f50b95bbd6aec
```

Artifact verifier:

```text
status=WARN
NONE=452
QUARANTINED=14
UNBOUND_LEGACY=49
blocking unquarantined STALE/TAMPERED=0
```

The quarantined artifacts carry no release authority. The legacy and
quarantined counts match the previously recorded baseline and were not
promoted by this slice.

Bounded DeepLuna Fast read-only audit:

```text
job=DS-005c5b9e54f8a2df60421f0e0f83973f
status=PASS
evidence_verdict=POSITIVE
negative_findings=0
scope_deviation=false
```

Sol independently ran the live-tree executable guard and locally accepted the
diff. Provider output did not establish the gate.

## Protected state

- `perfume_chem.db` remains zero bytes with SHA-256
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- test execution changed the knowledge-database byte hash, a known verifier
  side effect;
- one exact candidate was located inside the verified recovery package;
- the candidate matched the protected SHA-256 before replacement;
- the restored knowledge database has SHA-256
  `5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`;
- post-restore `PRAGMA integrity_check` returned `ok`.

No sensitive environment value or archive inventory is recorded here.

## Exit decision

The A2 Slice 3 gate passes because the backend remains sole persistence
authority, legacy duplicate writes fail closed, canonical projections are
read-only, import adapters cannot persist, the executable dual-write guard is
green, no legacy schema was deleted, and all required verification checks
passed. A bounded checkpoint commit is the final bookkeeping action.
