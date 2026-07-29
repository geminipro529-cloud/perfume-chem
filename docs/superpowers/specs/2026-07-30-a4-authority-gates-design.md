# A4 Authority and Mode Gates Design

## Decision

Implement one pure domain-policy module, `engine/authority_gates.py`, and reuse
it from the existing formula gate and versioned laboratory claim service.
Preserve `a2-claim-v1` as a read/write compatibility contract; enforce the new
dimension-complete evaluator for `a4-claim-v1`.

The user has already authorized uninterrupted execution through Build D, so
this written design records the approval boundary without another prompt.

## Considered approaches

1. **One domain-policy module with narrow adapters — selected.** This keeps
   actor transitions, operating modes, claim decisions, family evaluation, and
   regulatory scope in one typed vocabulary while allowing the pipeline and
   backend to remain persistence adapters.
2. Add more conditionals directly to `engine/pipeline/gates.py` and
   `backend/app/services/lab_science.py`. Rejected because it would preserve
   the existing stringly typed authority islands.
3. Store policy tables in new database tables. Rejected for A4 because the
   policy is deterministic code, no mutable policy administration is required,
   and a migration would not improve the negative-claim gate.

## Domain vocabulary

Enums exactly represent the six actors, eight action states, eleven operating
modes, five claim decisions, nine separately gated claim types, four
regulatory states, and stable denial/withholding reason codes.

`evaluate_transition(PermissionContext)` evaluates actor role, mode, current
state, requested state, evidence, safety, and human confirmation. AI may
propose but may not confirm, measure, commit, correct, or release. Terminal
states cannot be silently reopened.

`evaluate_mode_action(mode, action)` uses a complete allowlist for each mode.
An unknown mode or action fails closed. The existing pipeline mode gate calls
this function using `ReleaseGateConfig.mode` and a new explicit
`ReleaseGateConfig.action`.

## Claim authority

`ClaimAuthorityInput` contains each dimension named by A4.3 rather than an
average score. `evaluate_claim_authority` selects requirements by claim type:
identity, quantity, family, safety, sensory, analytical, and release evidence
are never substituted for one another. Contradictions block. Missing required
dimensions withhold. Partial documentary support can be advisory. Exact and
scoped decisions require their own complete conditions.

For `a4-claim-v1`, the backend reconstructs this input from
`authority_json`, `missing_evidence`, `conflicts`, evidence-link roles, and
human-review state. It rejects a caller-requested decision that is more
permissive than the computed result. Legacy `a2-claim-v1` remains compatible
and retains its existing exact-claim checks.

## Family and regulatory scope

`evaluate_family_gate` records archetype version, protected anchors, allowed
uncertainty, genre-shifting materials, target/current values, unknowns, and
evidence status. An undefined family withholds only the family-preservation
claim.

`evaluate_regulatory_gate` accepts a dated `RegulatorySnapshot`. Only a
complete, formal, effective, non-draft, conflict-free snapshot with no
unresolved critical item can return `PASS_FOR_DECLARED_SCOPE`. It never emits
certification language.

Mass/volume and raw/active basis failures continue to use the A3 quantity
system and its stable incomparability reasons; carrier presence alone is not a
failure.

## Verification

Tests are written and observed RED before implementation. They cover every
actor/state family, all eleven modes, each separately gated claim type, family
undefined/drift behavior, density/concentration basis behavior, all four
regulatory states, AI self-release, unsupported analytical and sensory claims,
and backend `a4-claim-v1` overclaim rejection. The canonical verifier gains
the module and tests.

No local software result is promoted to scientific release authority.
