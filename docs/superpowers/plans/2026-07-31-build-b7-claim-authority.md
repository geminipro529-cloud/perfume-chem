# Build B7 Claim-Specific Scientific Authority Implementation Plan

> Execute in strict order. Keep the A2/A4 gate unchanged, derive all promoting
> facts from canonical B1-B6 rows, and do not start B8 until the B7 exit gate
> passes.

**Goal:** Add an append-only, claim-specific B7 authority engine whose five-way
decision is reproducible from typed canonical support and whose negative tests
prove that heuristic or context-mismatched data cannot promote.

**Architecture:** Add `lab_claims` model, repository, and service modules.
Persist one versioned authority row plus typed support links. Keep the eleven
policies in a code-owned, content-hashed registry and snapshot each policy in
the authority row. A2 is historical context only.

**Runtime:** Use
`D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe`.
Run without a PTY, with `PY_COLORS=0`, `TERM=dumb`, `NO_COLOR=1`,
`--color=no`, and explicit timeouts.

---

## Task 1: Establish the B7 schema contract with failing tests

**Create:**

- `backend/tests/unit/test_b7_claim_authority_schema.py`
- `backend/tests/integration/test_b7_claim_authority_migration.py`

**Test first:**

1. Assert that `CLAIM_AUTHORITY_TABLE_NAMES` contains exactly
   `lab_claim_authority_versions` and `lab_claim_authority_support_links`.
2. Assert that both tables are included in `APPEND_ONLY_TABLES`.
3. Assert all decision, claim-type, role, typed-link-shape, version-chain,
   count, hash, and exact-decision constraints.
4. Assert typed foreign keys target the six B2-B6 canonical tables and the A2
   claim-assessment table.
5. Assert the migration revision is `20260731_0011` with down-revision
   `20260731_0010`.
6. Upgrade a scratch database, inspect both tables and triggers, prove
   update/delete fail, downgrade, and prove the B7 tables are removed.
7. Run the two files and preserve the expected red output before adding
   production code.

## Task 2: Add the model and migration

**Create:**

- `backend/app/models/lab_claims.py`
- `backend/alembic/versions/20260731_0011_b7_claim_authority.py`

**Modify:**

- `backend/app/models/lab.py`

**Implement:**

1. Define the eleven claim types, five decisions, three support roles, and six
   typed support kinds.
2. Add `LabClaimAuthorityVersion` with immutable scope, policy, decision,
   per-dimension results, evidence output, counts, review, and hash fields.
3. Add `LabClaimAuthoritySupportLink` with an exact-one typed foreign-key
   shape and derived-fact/source snapshots.
4. Register both tables with the canonical lab metadata and append-only set.
5. Create matching Alembic tables, indexes, constraints, foreign keys, and
   SQLite append-only triggers.
6. Re-run Task 1 tests until green.

**Checkpoint:** Commit only the schema, migration, aggregation import, and
schema/migration tests.

## Task 3: Define the complete code-owned policy registry

**Create:**

- `backend/tests/unit/test_b7_claim_authority_service.py`
- `backend/app/services/lab_claims.py`

**Test first:**

1. Assert exactly eleven policies and no aliases in the canonical registry.
2. Assert every policy declares all required B7 dimensions.
3. Assert policy canonicalization and SHA-256 are deterministic.
4. Assert no policy permits release, certification, universal safety, or
   formula mutation.
5. Assert exact-capable and scoped-only claim types match the frozen design.

**Implement:**

1. Add immutable `ClaimAuthorityPolicy` declarations.
2. Add a closed A2 claim-type alias map.
3. Add stable canonical JSON hashing and policy snapshots.
4. Add decision and dimension-result data classes.
5. Add computed wording for all five decisions.
6. Run the policy tests until green.

## Task 4: Resolve typed canonical support without caller booleans

**Create:**

- `backend/app/repositories/lab_claims.py`

**Modify:**

- `backend/app/repositories/lab.py`
- `backend/app/services/lab_service.py`

**Test first in `test_b7_claim_authority_service.py`:**

1. Resolve each of the six support kinds from an actual database row.
2. Derive B1 source references and independence groups.
3. Derive identity and condition scopes, evidence class, uncertainty, method
   validation, model applicability, safety, and upstream hashes.
4. Reject missing rows, duplicate links, a support-kind/FK mismatch, stale
   parent chains, and unsupported support kinds.
5. Prove caller A2 `authority_json` booleans do not appear in derived facts and
   cannot change a B7 result.

**Implement:**

1. Add persistence-only getters for B7 rows and required canonical upstream
   chains.
2. Add `ClaimAuthoritySupportInput` and `ClaimAuthorityEvaluationInput`.
3. Resolve B2 assertions and observations, B3 contexts/OAVs, B4 rules, B5
   analytical authority chains, and B6 profiles/snapshots.
4. Snapshot only derived facts and canonical source references.
5. Re-run focused tests until green.

## Task 5: Implement the fail-closed decision lattice

**Modify:**

- `backend/app/services/lab_claims.py`
- `backend/tests/unit/test_b7_claim_authority_service.py`

**Test first:**

1. Cover `ALLOW_EXACT`, `ALLOW_SCOPED`, `ADVISORY_ONLY`,
   `WITHHOLD_UNKNOWN`, and `BLOCK`.
2. Cover every claim type with at least one canonical positive or expected
   fail-closed path.
3. Prove `HEURISTIC`, `SPECULATIVE`, and `UNKNOWN` evidence never produces an
   exact decision.
4. Prove identity, grade/lot, matrix, route, endpoint, temperature, pressure,
   date, jurisdiction, category, and model-domain mismatches never promote.
5. Prove no confidence average can hide a failed critical dimension.
6. Prove failed QC/validation, unknown natural composition, failed or unknown
   regulatory state, unresolved conflicts, and insufficient source
   independence fail closed.
7. Prove release-grade wording is always forbidden.

**Implement:**

1. Evaluate each policy dimension independently.
2. Apply the strict decision order:
   `BLOCK` -> `WITHHOLD_UNKNOWN` -> `ADVISORY_ONLY` ->
   `ALLOW_SCOPED` -> `ALLOW_EXACT`.
3. Persist supporting observations, conflicts, missing requirements, source
   references, uncertainty, wording, dimensions, and canonical hashes.
4. Enforce exact-decision row shape before persistence.
5. Run the focused service suite until green.

## Task 6: Prove scope-preserving revisions and end-to-end reconstruction

**Create:**

- `backend/tests/integration/test_b7_claim_authority_e2e.py`

**Test first and implement as needed:**

1. Create an A2 historical claim, canonical B2-B6 support, and a B7 authority
   root in a scratch database.
2. Reconstruct the persisted result and typed links from canonical rows.
3. Add stronger evidence and create a latest-parent B7 revision.
4. Prove the claim type, A2 claim chain, subject, identity scope, condition
   scope, and claim scope cannot change within a revision chain.
5. Prove an upgrade to one scoped claim does not change any other claim.
6. Prove content hashes and reconstructed output are deterministic.
7. Run all four B7 test files until green.

## Task 7: Compatibility and static verification

Run in order:

1. B7 unit and integration tests.
2. A2 claim-science tests.
3. B1-B6 focused tests.
4. Authority-gate tests.
5. Alembic current-head and backup/restore tests.
6. Ruff on every B7-touched Python file.
7. Scoped mypy with `--follow-imports=skip`.
8. `git diff --check` on B7 paths.

Do not reinterpret a timeout as a result. Preserve stdout, stderr, duration,
exit code, and exact test count.

## Task 8: Independent final audit and B7 gate report

**Create:**

- `docs/verification/b7/claim_authority_gate.md`
- `docs/verification/b7/claim_authority_gate.json`

**Verify:**

1. Record branch, commit, migration head, runtime versions, archive proof, and
   exact test commands/counts.
2. Record protected database lengths, SHA-256 values, and read-only integrity
   results before and after verification.
3. Run a fresh exact-project `deepseek_check`.
4. If and only if readiness is `READY`, run one bounded DeepLuna Fast final
   audit with `NO_LUNA` and no Codex fallback.
5. Independently reproduce every actionable finding locally.
6. Fix verified findings with new failing tests, then repeat the focused and
   compatibility gates.
7. Commit only B7 implementation and verification paths.
8. Confirm the Git index is clean and unrelated dirty/untracked work remains
   untouched.

## Build B7 completion rule

B7 is complete only when the migration, database constraints, append-only
guards, eleven policy declarations, five decisions, typed support
reconstruction, negative promotion tests, compatibility tests, static checks,
protected-database proof, and final audit all pass. Only then may B8 begin.
