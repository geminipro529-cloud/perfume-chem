# DeepSeek Formula Worker Packet Template

## Packet identity

- Packet ID:
- Formula ID:
- Formula class:
- Target odor:
- Canonical inventory:
- Evidence bundle:
- Required row minimum:
- Parent manifest hash:

## Bounded task

Construct or revise one formula only.

Do not alter another formula.
Do not modify the canonical inventory.
Do not issue the program-level final pass.

## Required outputs

1. `formula.json`
2. `row_audit.json`
3. `interaction_map.json`
4. `arithmetic.json`
5. `meaningful_complexity_summary.json`
6. `ablation.csv`
7. `perturbation.csv`
8. `blockers.md`
9. `hashes.json`

All JSON must validate against `meaningful_complexity_schema.json`.

## Construction requirements

- High-complexity accord: at least 50 distinct odor materials after pruning.
- High-complexity perfume: at least 65 distinct odor materials after pruning.
- Carriers do not count.
- Duplicate strengths count once.
- Product bases count once.
- Microtexture rows may not exceed 20 percent.
- Every row must have a function, evidence class, dose rationale, interaction record, ablation class, and physical-confirmation state.
- No row may be kept only to meet the count.

## Interaction work

For every major module:

- list enhancing groups;
- list suppressing groups;
- list masking risks;
- list bridges;
- list collision risks;
- identify opening, heart, drydown, and late-drydown effects;
- write a physical test.

## Gate order

G0 canonical lock
G1 inventory
G2 arithmetic
G3 row count
G4 functional coverage
G5 interaction coherence
G6 dominance
G7 temporal architecture
G8 Monte Carlo
G9 ablation
G10 perturbation
G11 anti-collapse
G12 physical chemistry
G13 evidence
G14 quality score

Stop on hard failure. Do not continue to a cosmetic score.

## Terminal response format

- packet ID;
- execution state;
- artifacts created;
- counts;
- tests run;
- failures;
- blockers;
- formula hash;
- recommended next action.
