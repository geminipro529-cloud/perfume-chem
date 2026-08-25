# SolForge A-B-C-D Perfumery Program

**Status:** nonruntime candidate program. Formula, inventory, compounding,
sensory, safety, purchase, publication, and release authority remain false.

SolForge is the control plane around Perfume-Chem's evidence-producing modules.
It does not replace the perfumer with a scalar score. It turns a target into the
smallest useful experiment, records what was actually observed, learns only
within a declared comparison scope, and admits software only after a blinded
benchmark.

Complexity means target-linked perceptual depth, coherent richness,
relationships, transitions, texture, restraint, and testable hedonic
mechanisms. Ingredient count, prose length, novelty, darkness, and technical
density are not positive evidence. A sparse formula can be more complex when
its few materials create clearer relations and deeper temporal development.

## A — Authority and Aim

Inputs:

- exact source and lineage hashes;
- target identity and forbidden drift;
- TARGET / IDEAL formula reference;
- separately identified CURRENT-INVENTORY build reference;
- current V5 workbook bytes and stock basis; and
- declared safety and claim scope.

The target is defined before inventory mapping. Conflicting authority,
unresolved stock basis, or hash drift returns `HOLD`.

## B — Build and Bound

`engine/perception/architectural_delta.py` proposes zero or one ranked,
nonredundant intervention: `OMISSION`, `ADDITION`, `RATIO`, or an evidence-only
`NARY_DESIGN`. Count-based rationales, redundant additions, unsupported Neroli
promotion, generic musk layering, and unisolated n-ary synergy return `HOLD`.

The output is a controlled comparison packet, never permission to mutate or
compound a formula.

## C — Compare and Learn

`engine/sensory/ledger.py` binds every observation to protocol, sample,
assessor, repeat, timepoint, endpoint, presentation sequence, and schedule
hash. Missing cells remain missing; duplicate cells, order confounding,
unqualified within-sniff timing, or an assessor safety incident return `HOLD`.

When repeatability is required, the protocol must declare a maximum
within-assessor repeat spread. Every assessor is audited against that threshold.
An adverse event stops evidentiary promotion even when the remaining grid is
otherwise complete.

`engine/preference.py` fits target fidelity, depth, richness, and liking as
separate criteria. Ties remain indifference evidence, assessor-cluster
bootstrap is deterministic, and sparse, disconnected, unscoped,
order-confounded, or baseline-failing results remain `WITHHELD` or
`DIAGNOSTIC`.

## D — Decide and Deploy

`engine/perception/complexity_replacement_benchmark.py` uses three blinded
arms per case:

1. plain Sol xhigh;
2. the same model with the candidate module packet; and
3. a byte-length-matched inert packet.

Live execution is phase gated:

- screen first: 3 cases per module, 27 outputs maximum;
- each request freezes the exact natural-language dispatch envelope and its
  canonical payload under a SHA-256 hash, so the submitted bytes—not only the
  underlying case—are auditable;
- proceed only with at least 2/3 wins against each control and no critical
  regression; and
- confirmation only for modules whose `PROCEED` decision is recomputed from
  the actual hash-verified screen receipt. A caller-supplied decision that does
  not exactly match those frozen scores and critical checks is rejected.

Final admission requires at least 4/6 wins, median paired gain of at least five
points against both controls, and zero critical errors. Registry hash drift,
reproducibility failure, a critical regression, or an authority-boundary
violation triggers rollback to runtime-unreachable state. Rollback never
authorizes source or evidence deletion. Runtime remains unreachable after a
rollback until the last validated registry hash, false authority flags,
unreachable candidate imports, and focused freeze/ensemble tests are verified;
failed verification remains `HOLD_RUNTIME_UNREACHABLE` and requires fresh
admission.

## Evidence basis

- ISO 8586:2023: assessor selection and training:
  https://www.iso.org/standard/76667.html
- ISO 13299:2016: sensory-profile methodology:
  https://www.iso.org/standard/58042.html
- ISO 11136:2014: controlled hedonic testing:
  https://www.iso.org/standard/50125.html
- NIST mixture-design guidance:
  https://www.itl.nist.gov/div898/handbook/pri/section5/pri54.htm
- Mixture and concentration effects in olfaction:
  https://doi.org/10.1093/chemse/bjaa032
- Temporal Dominance of Sensations review:
  https://doi.org/10.1016/j.tifs.2014.04.007
- IFRA Standards documentation:
  https://ifrafragrance.org/initiatives-positions/safe-use-fragrance-science/ifra-standards/ifra-standards-documentation

These sources justify experimental and governance design. They do not prove
that any formula is beautiful, safe for release, stable, similar, or liked.

## Current transition

The partially observed v2 external run remains an unscored provenance
tombstone. The refreshed v3 corpus adds explicit sensory-stop and assessor
repeatability cases without changing v2 bytes. Three infrastructure attempts
were rejected without scoring: inherited project instructions contaminated a
local run, an oversized cloud dispatch exceeded capacity, and raw JSON did not
start a cloud response. The next external operation is a new v5 `SCREEN`
manifest with hash-bound dispatch text after exact model identity and fresh
projectless conversation capture can be proven.
