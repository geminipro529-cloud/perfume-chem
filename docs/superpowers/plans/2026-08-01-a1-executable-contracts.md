# Build A Phase A1 Executable Contracts Plan

Date: 2026-08-01

Authority: `SOL_5_6_PERFUME_CHEM_MASTER_A_D_PROMPT.md` lines 998-1220 and the
current `D:\chatbots\perfume-chem` working tree. Historical A1 reports are
evidence only.

## Baseline

- A0 exit gate: passed.
- A1 starting SHA: `0fa0adff1533ffca1ad74e6e6904b1afc1b1d435`.
- Supported runtime: `.venv_py311_a0` / Python 3.11.
- Fresh A1 first run: 75 passed in 0.61 s, stderr empty.
- First-run stdout SHA-256:
  `c5d6a3fdefd355f7f1ec6d14702c1b08644ff5f53b91c387bdb9a00b13887865`.
- First-run JUnit SHA-256:
  `efd1f28f09de2c19477d43c8f84885b04a75025aec40e9f7ba590d00892da855`.
- DeepLuna Fast gap audit `DS-bbc94fa53407e67f374424a6aba4ab9f`
  returned PASS, but Sol rejected its no-gap conclusion after local line-level
  review found requirements that the worker missed.

## Current disposition and RED hypotheses

| Contract | Current evidence | Planned action |
|---|---|---|
| A1.1 diluent accounting | Core implementation and conservation tests pass. DEP/IPM are tested only at classifier level, not full 10% accounting. | Add explicit parameterized accounting cases for DPG, DEP, TEC, and IPM. No production change unless RED. |
| A1.2 target rows | Implementation carries every accepted field and namespaces unknown fields. The strongest test does not directly compare every input field. | Strengthen the authoritative test to compare every accepted field and round-trip representation. No production change unless RED. |
| A1.3 anti-compression | Three-valued result and 12-axis cardinality exist. `_check_same_cas` ignores declared stereochemistry/origin/chemotype; `_check_same_supplier_grade` ignores supplier product and lot. Historical neat/dilution and Hedione tests assert only that results exist. | Add RED tests for same-CAS/different stereochemistry, natural origin or chemotype, and same-grade/different-lot; strengthen physical-stock and tri-state assertions; minimally make the two identity axes compare declared dimensions without changing the 12-axis API. |
| A1.4 correction replay | Missing/cross-stream/cycle/stale/conflicting retry and three-link immutable replay are covered and pass. | Retain as confirming tests; no change unless a broader gate contradicts this. |
| A1.5 empty inputs | Primary target, roster, candidate, budget, and rank denominator guards exist. `restore_from_roster` accepts empty rosters and `reconcile_total` silently returns on a zero denominator. `generate_ensemble` lacks a direct empty-input contract test. | Add RED tests for both empty restore rosters and zero/empty reconciliation; add direct confirming tests for empty ensemble input; implement only the missing stable domain guards. |
| A1.6 identity vs inventory | Independent enums and exact/alias/unresolved, exact-lot, grade mismatch, functional substitute, and absent-stock behavior exist. AMBIGUOUS and NOT_TECHNICALLY_REQUIRED behavior lacks direct assertions. | Add confirming behavior tests; no production change unless RED. |
| A1.7 identity conservatism | Same-CAS grade/lot, natural origin, controlled grade, opaque base, missing CAS, and registered trade-material tests pass. | Retain; cross-link anti-compression RED cases rather than duplicate identity-resolver logic. |
| A1.8 strengthen tests | Historical A1 tests contain existence-only and bool-compatibility assertions. | Strengthen those assertions in place and record before/after rationale in the A1 disposition report. Do not delete existing coverage. |

## Execution sequence

1. Create and verify a path-preserving targeted pre-edit archive for every file
   that may be changed.
2. Add the A1.1/A1.2/A1.3/A1.5/A1.6 assertions first.
3. Run only the new/strengthened nodes and capture the expected RED failures.
4. Apply minimal production changes to:
   `engine/reconstruction/anti_compression.py`,
   `engine/reconstruction/quantity_inference.py`, and only any other module
   proven RED by the new tests.
5. Run focused GREEN tests, then the complete A1 contract pair.
6. Write the explicit A1 disposition table with first-run, RED, source,
   minimal fix, final result, and verifier impact.
7. Prove shard coverage exactly once, all engine shards, complete backend
   tests, and the canonical top-level verifier.
8. Run a fresh exact-project DeepLuna check and a bounded Fast final audit.
   Sol independently verifies and accepts or rejects that result.
9. Create a bounded A0/A1 checkpoint SHA containing only the approved A0/A1
   evidence and A1 changes. Do not stage unrelated dirty work.

## Stop conditions

- Any schema or migration requirement returns to the A0 ADR; A1 does not
  authorize schema expansion.
- Any conflict with unrelated user work stops that individual edit, not the
  rest of the deterministic audit.
- A1 does not pass on focused tests alone. The full exit gate at master lines
  1208-1220 remains authoritative.
