# ADR: C0 physical-model consolidation and runtime ownership

Date: 2026-08-02
Status: accepted for Build C implementation
Decision owner: Sol

## Context

The repository has multiple headspace, release, temporal, phase, receptor,
diffusion, skin, hedonic, longevity, and sillage calculations. They do not share
one request contract, condition model, property authority, applicability policy,
or validation status. A caller can therefore obtain materially different answers
to a similarly named claim.

The current canonical workbench uses
`engine.pipeline.formula_state.build_formula_state` for modeled headspace/OAV and
`engine.pipeline.simulator.simulate_formula` for temporal screening. It correctly
withholds calibrated longevity, sillage, and receptor outputs. Standalone thermo,
reconstruction, optimizer, backend-domain, and script paths remain present.
UNIFAC is explicitly inactive; DIPPR-style equations and COSMO-RS are unsupported.

Build B selected assertions in Laboratory Beta are the property authority, but
current model implementations still read registry/profile scalars directly.

## Decision

Build C will introduce a versioned `engine.physics` boundary. A model request must
name the claim, formula-state reference, Build B property snapshot, matrix,
application environment, exact conditions, and requested model version. A result
must report model identity/version, C0 classification, computed/withheld status,
values and units, conditions, applicability, uncertainty, evidence references,
assumptions, warnings, and canonical input/result hashes.

For each claim type and model version, the router permits **one selected implementation**.
There is no fallback to a differently named headspace, release, sillage, or
perception engine. Missing prerequisites return `WITHHELD` or `NOT_APPLICABLE`.

The canonical runtime direction is:

```text
endpoint, report, or optimizer
  -> PerfumeWorkbench or canonical Laboratory Beta application service
  -> engine.physics router
  -> one versioned implementation
  -> immutable result envelope
```

Physical properties enter through a condition-aware adapter over **Build B selected assertions**.
**Laboratory Beta** SQL records remain persistence authority. Model code is pure
computation and may not write canonical records or create a second truth store.

## Claim-family routing decision

The following table is exhaustive for the C0 claim families. It selects one
structural runtime path per supported claim while keeping all C0 behavior
unchanged. A current compatibility authority remains the only answer-producing
path until its named Build C gate passes; afterward the `engine.physics` router
may select exactly one versioned implementation. Every other path is advisory,
fixture-only, deprecated, or `WITHHELD` and may not silently answer the same
request.

| Claim family | Current C0 authority | Post-gate canonical owner | Competing-path disposition |
| --- | --- | --- | --- |
| Property scalars and vapor pressure | Build B selected assertions; exact equation helpers remain arithmetic only | C1-C3 condition-aware property adapter and versioned router | Registry/profile shortcuts and estimates cannot override the selected assertion or its applicability |
| Equilibrium headspace and OAV | `build_formula_state` compatibility output with `HEURISTIC_NOT_MEASURED` | C4 equilibrium result through `engine.physics`; C8 adds OAV/mixture-interaction policy | Standalone thermo, analyzer, reconstruction, and script outputs remain advisory or fixture-only |
| Activity coefficients, phase, and Hansen distance | Current pipeline phase gate is advisory; ideal/Raoult arithmetic and Hansen scores retain separate labels | C4 versioned equilibrium/phase claim with explicit matrix, conditions, and applicability | Heuristic Hansen risk cannot masquerade as a calibrated activity coefficient or equilibrium result |
| Temporal release and trajectory, diffusion, projection, and skin/fabric behavior | `simulate_formula` is the temporal compatibility authority; optimizer modules are advisory | C6 dynamic-release result; measured longevity/sillage endpoints remain gated through C9 | Alternate trajectory, diffusion, skin, and projection modules remain `LEGACY_HEURISTIC` or advisory until separately validated |
| Natural-material decomposition | Generic constituent profiles are low-authority proxies only | C7 lot-aware decomposition through `engine.physics` | Generic profiles cannot answer a supplier-lot or batch-composition claim |
| Maturation, aging, and storage | Existing shelf-life and reaction outputs are advisory heuristics | C9 may admit only evidence-supported, applicable claims | No heuristic may become a stability or shelf-life claim by naming alone |
| Receptor, adaptation, dose-response, psychophysics, and hedonic | Quarantined or optimizer-advisory paths; canonical workbench outputs stay withheld | C9 evidence triage selects one supported version or preserves `WITHHELD` | Family priors, fixed valence, and response transforms cannot become biological or sensory validation |
| Longevity and sillage endpoints | Canonical workbench returns `null`/`UNKNOWN`; backend note rules are legacy | C9 evidence triage plus named empirical endpoint evidence | Backend hour/class rules and optimizer composites remain fixture-only or advisory |
| UNIFAC, DIPPR-style, and COSMO-RS | Inactive stub or `UNSUPPORTED` | No Build C owner without a separate evidence-backed implementation decision | Always `WITHHELD`; labels, imports, or partial tables cannot imply capability |

C10 optimization consumes only versioned router results and their abstentions; it
does not select a second physical engine. This table chooses ownership and
disposition, not scientific validity. Each later phase must still pass its own
evidence and applicability gate before a compatibility authority can be replaced.

## C0 compatibility disposition

- `build_formula_state` remains the compatibility adapter for current headspace
  until the C4 equilibrium gate passes.
- `simulate_formula` remains the compatibility adapter for current temporal frames
  until the C6 dynamic-release gate passes.
- generic natural constituent profiles remain low-authority proxies until the C7
  lot gate passes.
- standalone thermo, reconstruction, optimizer, backend-domain, and script engines
  retain the exact runtime/advisory status recorded in the C0 inventory.
- workbench longevity, sillage, and receptor outputs remain withheld.
- legacy behavior is frozen only as `LEGACY_HEURISTIC` regression evidence. It is
  not scientific validation and cannot promote a claim.

**C0 changes no production runtime path.** It adds inventory, architecture,
fixtures, and verification only. No model implementation, caller switch, database
migration, or canonical data mutation is authorized by this ADR.

## Consequences

Positive consequences:

- callers cannot silently select competing models after the router is implemented;
- model and property versions become reproducible;
- applicability, uncertainty, and abstention become part of every physical claim;
- legacy migration can be measured against frozen outputs without treating those
  outputs as truth.

Costs and constraints:

- later phases must implement adapters before changing callers;
- selected-assertion access must be made available as a read-only snapshot to pure
  engine code;
- heuristic outputs may remain useful for diagnostics but must keep non-promoting
  labels;
- removal of legacy modules requires a proven-empty caller graph and separate
  migration evidence.

## Enforcement

`scripts/verify_c0_physical_model_inventory.py` validates inventory coverage,
classifications, symbols, callers, source hashes, unsupported-capability absence,
ADR statements, and legacy fixture replay. The C0 exit gate fails closed if any
record becomes stale or any fixture loses its warning/hash binding.
