# Build B10 scientific-data authority verification design

## Decision

Build B10 is a verification and evidence-packaging phase. It adds no
production model, service, endpoint, migration, backfill, or scientific
value. Its authority comes from current executable tests, the canonical
Build B gate records, deterministic inventory checks, protected-database
checks, and a final bounded independent review.

The two required final artifacts are:

- `docs/verification/scientific_data_authority_report.md`
- `docs/verification/scientific_data_authority_report.json`

The machine report is the source for exact counts and gate state. The
Markdown report is a human-readable rendering of the same evidence. Neither
artifact is scientific-release authority.

## Scope and authority boundary

In scope:

- reproduce all nineteen B10 test categories against current code;
- run the repository's supported full non-Docker verifier;
- verify the frozen B0 inventory artifact and current Build B gate records;
- distinguish legacy inventory from canonical migrated data;
- report conflicts, selection policy, contextual threshold authority,
  knowledge-rule status, analytical validation, regulatory snapshots, and
  runtime call-graph change;
- record remaining unknowns and exact claim wording; and
- prove that protected databases and pre-write worktree recovery remain
  unchanged.

Out of scope:

- new scientific observations or literature promotion;
- production database migration or population;
- modification of legacy scientific consumers;
- Build C implementation;
- legal approval, safety certification, performance proof, or release
  approval.

Sol remains the final architecture, science, security, provenance, and gate
authority. DeepLuna Fast is bounded to read-only coverage and adversarial
review.

## Baseline and final SHA definitions

The report removes ambiguity by recording four Git checkpoints:

1. Build B baseline gate commit: the commit that established B0;
2. final runtime implementation commit: the last production-code commit in
   B9;
3. final pre-B10 gate commit: the committed B9 gate package; and
4. B10 report-input commit: the last test/design commit before report
   generation.

The report also records before/after SHA-256 values for the protected
databases and the B0 compressed/decompressed inventory.

The report commit cannot contain its own SHA without a circular mutation, so
the final handoff records the evidence-package commit separately.

## Canonical inventory model

The B0 inventory remains the frozen before-migration source of truth for
legacy scientific values. B10 must independently verify:

- the compressed and decompressed inventory digests;
- source digest, material, property-observation, code-constant,
  knowledge-rule, and conflict-set counts;
- authority-label counts; and
- forbidden/generated path count.

Canonical migrated data are reported separately from legacy inventory.
Build B migrations intentionally create empty append-only tables and promote
zero legacy rows. Synthetic records in isolated tests prove the contracts;
they are not production observations.

No aggregate evidence or coverage percentage is allowed.

## Required test matrix

The final machine report contains exactly nineteen rows:

1. source ingestion and digest verification;
2. exact locator preservation;
3. duplicate and independence grouping;
4. observation round trips;
5. selected-assertion conflict handling;
6. unit conversion and incompatibility;
7. contextual ODT matching;
8. strict science mode;
9. OAV claim boundaries;
10. rule compilation and invalid-reference prevention;
11. analytical method validation;
12. calibration, QC, and uncertainty;
13. GC-O alignment;
14. raw-file attachment and digest;
15. regulatory dates and snapshot versioning;
16. natural contribution aggregation;
17. negative authority promotion cases;
18. API and report provenance; and
19. export, import, backup, and restore.

Each row records concrete test nodes or test files, current result, and the
authority boundary it proves. A historical gate PASS cannot substitute for a
current test execution.

## Runtime call graph

The before graph is the B0 legacy path:

```text
legacy constants/YAML/JSON/SQLite
  -> direct engine consumers
  -> calculations/recommendations/safety helpers
  -> output claims
```

The after graph is the canonical Build B authority path:

```text
B1 source document/extraction/workflow
  -> B2 typed observation/conflict/selected assertion
  -> B3 contextual threshold/OAV
  -> B4 compiled rule
  -> B5 validated analytical run/QC/claim assessment
  -> B6 dated regulatory snapshot/finding
  -> B7 claim-specific authority decision
  -> B8 non-promoting gap priority
  -> B9 read-only strict/exploratory JSON, Markdown, and UI
```

Legacy data do not enter that graph unless explicitly adapted and retained as
heuristic or otherwise non-promoting evidence.

## Exact claim wording

The report copies the code-owned B7 wording for:

- `ALLOW_EXACT`
- `ALLOW_SCOPED`
- `ADVISORY_ONLY`
- `WITHHOLD_UNKNOWN`
- `BLOCK`

It also lists the forbidden phrases `release-grade`, `certified`,
`universally safe`, and `unscoped equivalence`.

The report itself uses no affirmative scientific-release wording.

## Artifact contract test

A new root test validates the final JSON/Markdown pair:

- required schema, checkpoints, inventories, and report sections exist;
- all nineteen test categories and ten Build B completion criteria are
  present exactly once;
- all eight evidence classes remain explicit;
- claim wording matches the code-owned B7 wording;
- unknowns and no-release boundaries remain visible;
- JSON and Markdown agree on status and authority boundary; and
- credential-shaped values and prohibited score fields are absent.

The test is written RED while the required report files are absent.

## Verification sequence

1. Verify and freeze the design and plan.
2. Run the exact nineteen-category scientific test set.
3. Run the repository's full non-Docker verifier with the supported Python.
4. Write the artifact-contract test RED.
5. Assemble the machine and Markdown reports from current evidence.
6. Run the report test and the final Build B compatibility slice.
7. Run Ruff, mypy, Alembic, immutable SQLite, archive, digest, ANSI, and
   credential-shape checks.
8. Run a fresh exact-project DeepLuna Fast final audit.
9. Reconcile every external claim locally, seal the reports, commit exact
   paths, and stop at the Build B boundary.

## Exit gate

Build B10 passes only if:

- all nineteen required test categories have current executable PASS
  evidence;
- the full non-Docker verifier passes;
- the B0 inventory and every Build B gate reconcile;
- all ten Build B completion criteria are explicitly satisfied;
- protected databases and the recovery archive verify;
- the final reports are internally consistent and free of secrets/ANSI;
- final independent review has no unresolved material finding; and
- no scientific-release claim is made.

Any failed current test, unexplained inventory discrepancy, stale migration
head, protected-state change, unsupported claim, or unresolved authority gap
blocks Build B and prevents Build C.
