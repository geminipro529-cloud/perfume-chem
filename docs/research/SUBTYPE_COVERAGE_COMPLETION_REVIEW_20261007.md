# Subtype implementation and application handoff — v5

Date: 2026-10-07. User scope: finish subtype work first; exclude speed
optimization. This is a supported implementation/disposition pass, not an
exhaustive perfume-science or release-completion claim.

## Outcome

The active source-bound bridge advances from **47 mappings / 93 options** to
**104 mappings / 168 options**, preserving the ordered predecessor mappings and
v1-v4 bytes. Every one of the 132 previously unmapped cards now has an explicit
reviewed disposition. No generic catch-all is counted as a specific subtype.

| Disposition | Reviewed cards | Still without an executable mapping |
|---|---:|---:|
| Architecture addition | 55 | 0 |
| Exact product/grade comparison | 32 | 31 |
| Controlled omission | 18 | 17 |
| Evidence or target input | 27 | 27 |
| Total | 132 | 75 |

The 75 remaining cards are not declared implemented experiments or validated
scents. The exact missing product, control or evidence requirements remain in
the [disposition manifest](../../data/formulation_knowledge/subtype_implementation_dispositions_v1.json).

## What changed

1. Added closed own-odor operation contracts and source-bound options across the
   remaining floral, fruit, aromatic, tea, gourmand, musk, woody and resinous
   families. Narrow exact-product refinements preserve canonical role quantities
   and protected constraints. Supplier suggested applications, synergy partners,
   negated descriptions and botanical origin cannot supply own-odor roles.
2. Applied avoid constraints to the whole comparison, including its background.
   Missing odor words cannot prove absence; zero smoke weighting cannot certify
   a smoke-free resin. Source-review receipts must match current canonical bytes.
3. Added optional fixed-row omission planning. Retained rows are unchanged;
   explicitly identified carrier blanks restore total mass, not fragrance-active
   mass. Decimal arithmetic is bounded and exact. No re-solving, imagined removal
   from an existing bottle, or automatic physical action occurs.
4. Added closed durable `OMISSION_COMPARISON_PLAN`, its additive migration, API
   tests and optional Experiments UI. Protocol output is planning-only, not a
   privately blinded or executed session. Casual observations remain lightweight.
5. Preserved a clause boundary between diagnostic titles and actual briefs so
   title negation cannot erase a separate positive request. Explicit avoid
   constraints still apply.
6. Recovered the actual Terre-heart CHIMIE L'HOMME reference from saved chat
   material and corrected the application message. See the
   [recovery report](CHIMIE_LHOMME_CHAT_RECOVERY_20261007.md). Neither Sport Citrus
   nor a nominal 30 mL statement is substituted for exact physical history.

Primary-source decisions and limits are documented in the
[pre-edit plan](SUBTYPE_COVERAGE_COMPLETION_PLAN_20261007.md), including exact
Gamma Coeur, Helvetolide, Exaltolide and labdanum descriptions. These sources
support bounded role hypotheses, not doses, calibrated performance or liking.

## Verification

The frozen staged v5 corpus passed **67 cases / 268 design executions**, including
reverse-order replay and unchanged input snapshots. There were 42 viable
comparison outcomes and 40 verified empty-stock-pool outcomes across 82
per-case option outcomes. This is not a claim that all 75 new options are
currently feasible. The corpus predates the final activation, title-boundary,
omission-precision and recovery changes; those received focused verification.

Key focused runs (overlap; do not sum as unique tests):

- Root v5/omission/historical contracts: 354 passed.
- Post-activation contracts: 199 passed.
- Title-boundary/v5/replay checks: 316 passed.
- Final recovery/botanical/subtype checks: 131 passed.
- Managed loopback launcher: 1 passed.
- Backend omission/API/populated migration checks: 32 passed.
- Repaired current-head backup/restore/migration checks: 12 passed.
- Final source and recovery fingerprint checks: 14 passed.
- Scoped Ruff/mypy, JavaScript syntax and `git diff --check`: passed.
- Final quick project verification: **10 checks passed**, partial scope only.

The earlier full-project verifier **failed**. Its original report is preserved:
[full report](../../output/subtype_v5_full_20261007.json). Three migration-head
assertion failures were repaired and focused retested. Remaining findings include
Python 3.14/protobuf collection incompatibility, stale inventory/range and
historical source-byte fixtures, commercial gate/scenario regressions, complexity
census/import failures and a full-backend timeout. Docker was skipped. No full
rerun or merge/release readiness claim follows from focused green results.

Exact hashes, per-run counts, residual failure groups and live receipts are in
[progress v13](../../data/formulation_knowledge/research_coverage_progress_v13.json).

## Live handoff

The existing local launcher now supports an explicit loopback host and manages
its worker. The application is running at `http://127.0.0.1:8000/app` on schema
`20261007_0025`. A consistent pre-upgrade SQLite backup was retained; populated
upgrade/downgrade/upgrade and downgrade refusal with an omission job were tested.

Three final real-worker diagnostics verified:

- Mineral-wood source-bound comparison despite a negated diagnostic title.
- Read-only equal-mass omission plan with fixed retained doses.
- Recovered CHIMIE L'HOMME context, with generation correctly withheld.

Event chains and result hashes verified for all three. Only diagnostic job
records were created. Database counts for bottles, experiments, formula versions
and bottle events remained zero; foreign-key checks remained clear. Static UI,
JavaScript and API paths were checked; no interactive browser-click test is
claimed. Current PID values are a handoff snapshot, not permanent identifiers.

## Boundaries and remaining work

Speed optimization remains explicitly untouched. Existing formulas, inventory
and unrelated dirty work were preserved. Orris Liquid remains excluded. No new
pipeline script, purchase, compounding, sensory result or empirical promotion was
created; no Git commit or push was performed.

Further scent validation needs actual observations. Exact-product comparisons
need their particular products; omission experiments need a specified control.
Neither requirement applies as blanket paperwork for casual personal research.
The implementation now records those distinctions rather than fabricating
executable coverage or claiming that more ingredients make a better perfume.
