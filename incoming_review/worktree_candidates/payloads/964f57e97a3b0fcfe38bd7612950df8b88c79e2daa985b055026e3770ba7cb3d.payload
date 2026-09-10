# Computer-only hedonic development

User-approved contract, 2026-09-09: no physical trial or sensory feedback is
required before producing the selected composition. No automatic bottle edits.

## Implemented search controller

`engine.optimizer.gate_aware.optimize_hedonic_design` is a separate callable
from `optimize_until_release_ready`. It never calls the release-gate repair
loop. It accepts a baseline, a computational evaluator, fixed named criteria
and scenarios, explicit stock bounds, directed dose transfers and step sizes.

The evaluator returns nonnegative target losses, with zero meaning a specified
computational target is met. Every criterion in every scenario is protected:
an improvement in body cannot purchase a regression in gin identity. Among
eligible candidates the lowest total loss wins. Scales must be specified by
the adapter, not learned or relaxed by this search. Rejected candidates and
accepted changes are recorded. Candidate evaluations are cached.

Transfers preserve the numerical total in the caller's declared units.
This does not establish constant active dose or carrier mass when stock
strengths differ. A composition constraint callback must enforce those
conditions using resolved stock forms. It receives a copy of each candidate.

Search tries smaller steps when a neighborhood gives no improvement, resets
to the first step after an accepted improvement, and stops at:

- COMPUTATIONAL_TARGET_MET: all specified losses are zero.
- PLATEAU: no admissible improvement in the declared neighborhoods/steps.
- EVALUATION_UNAVAILABLE: missing, invalid, or failed evaluation prevents a
  supported decision. Missing evidence is never a perfect score.
- BUDGET_EXHAUSTED: round limit reached; incumbent retained.

No state requires a preliminary physical mix. Every result explicitly says
COMPUTATIONAL_DESIGN_ONLY and sensory_validated=false. A plateau is local,
not proof of a globally optimal formula. Safety evaluations remain separate;
this controller does not confer release authority.

## Gin Vetiver Cypress EDP integration status

### Evidence-portfolio CLI mode (current, 2026-09-09)

`optimize_evidence_portfolio` now supplies independent proposal enumeration,
a bounded deduplicated archive, parallel evaluation, explicit loss intervals,
non-dominated alternatives and recursive robust advancement. It enumerates even
from an all-zero baseline. It never infers intervals from supplier descriptions.
Every candidate upper loss bound must be no greater than the incumbent lower
bound on every criterion/scenario; at least one must improve by the declared
minimum. Identical nondegenerate intervals are not proof of nonregression.

The search representative is the smallest raw change among robust improvements,
with deterministic stock-vector tie breaking. It is traversal state, NOT the
unique best perfume. The returned frontier retains evaluated, quantitatively
covered alternatives that cannot be robustly dominated. No summed hedonic score
resolves conflicting criteria. Callers provide finite, bounded, thread-safe
evaluators; interval provenance and scenario context are required. Supplied
`validated_prediction` labels are caller assertions, not independent validation
performed by the controller. This mode does not rewrite or admit evaluator code.
The separate older concurrent API retains its explicit revision mechanism.

Stops distinguish `LOCAL_PARETO_PLATEAU`, `UNRESOLVED_COMPARISONS`,
`EVIDENCE_BOUNDARY`, and `BUDGET_EXHAUSTED`. A plateau covers only evaluated
neighborhoods around visited representatives, not a global optimum or exhaustive
exploration of all branches of the frontier. No stop constitutes skin release or
observed liking. Invalid evaluations preserve diagnostics and cannot select.

Reproducible invocation, using the existing script (no new pipeline script):

```powershell
.venv/Scripts/python.exe scripts/verify_formula_workflow.py --formula-file formulas/records/Gin_Vetiver_Cypress_Air_30mL_v4_EDP.json --design-plan data/design_briefs/gin_vetiver_edp_evidence_v1.json
```

This branch reads a JSON formula, verifies formula/inventory hashes and every
exact current stock ID/form, and freezes diluted/carrier-bearing stocks. It
writes only a generated JSON receipt under `output/design_portfolios`. It does
not call the release pipeline, create a mixing card, modify the formula, or
require preliminary physical mixing. The full profiles and source hashes travel
with the receipt. Changed source bytes require deliberate re-review and rebinding,
not silent replacement of inventory authority metadata.

The supplied gin-vetiver plan uses `evaluate_design_roles`: an evidence-linked
qualitative adapter, with no numerical mixture predictions. Manufacturer roles
and original formula design intentions are explicitly distinguished in profiles.
It describes roles of increased/decreased stocks; those are not predicted
perceived gains/losses. Missing profiles remain listed, not dropped.

Actual result: baseline plus 71 feasible alternatives (72 records); all 18 stocks
matched. The old 15 raw-group-retention rejections are no longer treated as
scientific failures. The 56 earlier ties are included. Three source-linked
priority hypotheses expose 3/3/2 unranked dose variants. Status remains
`EVIDENCE_BOUNDARY`; formula unchanged, predicted liking null. The runtime works,
but a calibrated full-perfume richness/layering/liking evaluator remains absent.
Do not describe this integration as a trained hedonic optimizer or as having
selected an improved physical formula.

### Concurrent structural mode (2026-09-09 update)

`engine.optimizer.gate_aware.optimize_concurrent_hedonic_design` now runs
named transfer lanes in a bounded thread pool. Every round starts each lane
from the same incumbent and evaluator version. The parent selects one whole
candidate, never a sum of independent lane edits. Each candidate must preserve
all hard composition constraints and must not regress any declared criterion
in any scenario relative to the round incumbent. Among eligible candidates,
the smallest summed loss wins, with deterministic lane-order tie retention.

`engine.hedonic_model.structural_design_losses(report, objectives)` allows
explicit structural objectives even when liking evidence is unavailable.
It rejects target-identity violations, empty objectives and invalid losses.
The caller supplies frozen objective definitions and scales; this function
does not generate a body, quality, or preference model from raw amounts.
Liking remains null rather than becoming a penalty or a fabricated score.

Evaluator improvements are supplied as uniquely versioned callbacks through
`revisions`. Their fixed `admission_cases` run alongside formula search. Each
case specifies a formula, scenario and acceptable interval for every criterion.
An admitted revision must also successfully rescore the original baseline,
incumbent and retained lane-winner shortlist before it becomes active. Adoption
occurs only at the round boundary. Failed revisions leave the old evaluator
active and receive a rejection receipt. Search and selection versions are
recorded separately; caches are version-local and coalesce duplicate requests.

This is controlled evaluator replacement, NOT self-modifying code. Fixed tests
must include identity removal, excessive accents, support overload, scenario
regression and missing-data examples appropriate to the adapter. Passing them
does not prove liking. No code here changes or relaxes those test intervals.
Callbacks must be pure, thread-safe and bounded; the thread pool does not kill
hung callbacks. Worker count and search rounds are configurable. Objectives
must have comparable predeclared scales. Conservative per-criterion protection
can plateau; the controller does not silently enable aesthetic tradeoffs.

Stops remain computational target met, plateau, evaluation unavailable or
budget exhausted. No preliminary mixing is required. No safety/IFRA score is
an optimization objective, and no release authorization is produced.

Verification: `tests/test_concurrent_hedonic_design.py` exercises real lane
overlap, recursion, parent selection, hard constraints, evaluator admission,
rescoring and missing-data separation. The controller is callable, not wired
to the release CLI. The current EDP formula remains unchanged; a calibrated
gin-vetiver structural evaluator and its end-to-end selection remain separate
integration work. The historical liking-blocked run below is not the behavior
of the new structural mode.

Update 2026-09-09: `engine.hedonic_model.evaluate_targeted_hedonics` now
separates composition constraints, experimental binary liking and evidence
coverage. `targeted_hedonic_losses` connects this report to the controller,
with explicit opt-in for experimental estimates. The actual EDP invocation
stops at missing matched liking evidence; there is still no trained
full-perfume predictor or selected revised formula. See
`docs/verification/GIN_VETIVER_TARGETED_HEDONICS_20260909.md`.

The following describes the earlier controller-only stage and the remaining
full-perfume adapter requirements:

The controller is tested on synthetic, hand-checkable objectives. It is not
yet wired to the gin-vetiver formula or the CLI; no new formula has been
selected by it. Do not describe controller tests as perfume validation.

The adapter must bind the existing formula and inventory identities; preserve
grapefruit FCF, light cypress, Hedione permission, no jasmine accord, and DEP
accounting. Freeze target-linked definitions for gin identity, vetiver body,
cypress prominence, citrus-middle continuity, woody density and drydown
definition. Do not substitute raw OAV shares, ingredient counts, release gate
totals, or generic pleasantness priors for those perceptual targets.

Before an end-to-end optimization, verify that the chosen evaluators actually
distinguish deliberate anchor removal, excess cypress, and excessive support
in the expected direction. Record their limitations and scenario provenance.
Any unsupported dimension remains unavailable rather than receiving invented
validation. The next engineering step is this adapter and its discrimination
checks, entirely computational. It does not require the user to mix anything.

## Current bounded closure: 2026-09-09

This update supersedes the earlier adapter-not-wired next-step statements above.
The existing `verify_formula_workflow.py --design-plan` branch now runs the
actual v4 gin-vetiver EDP record through a source-bound evidence portfolio.
Adding `--evaluator-review` verifies formula, plan and evidence-file hashes,
adjudicates all declared evaluators, and emits an explicit final decision.
The inventory workbook/snapshot/overlay hashes are bound to the same
materialization used to validate exact stocks. No inventory pins are changed.

Every proposal event is retained, including bounds/constraint rejection,
duplicates and budget exclusion. Pending or inconsistent ledgers cannot
produce a completed decision. Errors, incomplete budget, incomplete review
and incomplete search are distinct from a completed no-change decision.

The final actual run accounted for 156 proposals, evaluated 71 feasible
alternatives plus the baseline, and ended with `NO_SUPPORTED_CHANGE`:
bounded run complete, baseline retained, full-perfume hedonic optimization
not achieved. All nine evaluator reviews have a disposition. Unsupported
numerical methods were excluded rather than allowed to select new doses.
No preliminary mixing is required, and no endless research task remains
mandatory for this version's bounded decision. New applicable evidence or
changed inputs can reopen it. Full project release remains blocked separately.

See `docs/verification/GIN_VETIVER_OPTIMIZER_CLOSURE_20260909.md` for the
finished checklist, final receipt, exact reproduction command and test results.
